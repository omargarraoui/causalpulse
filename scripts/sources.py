"""
Source-wise GP-prior generative model for news embeddings.

This module is a faithful translation of StrADiff (Wei, 2026, arXiv:2604.04973) to
the news domain. The observation matrix Y ∈ R^{N×d} (N article embeddings of
dimension d) is modeled as the output of a mixing map gφ applied to a source
matrix S ∈ R^{N×K}, where each column of S is the activation trajectory of one
of K latent causal forces across the articles, ordered by publication time.

The decisive structural commitment, taken verbatim from the paper, is that the K
source columns are NOT coordinates of a shared latent code. Each column has its
own generative path: its own learned Gaussian starting parameters (μ^(k), σ^(k)),
its own reverse diffusion network ε_{θ_k}, and its own GP prior with its own
learned length-scale ℓ_k. The four loss terms (paper Eq. 68) are optimised
jointly within a single end-to-end objective:

    L = L_rec + λ_p · L_prior + λ_d · L_diff + λ_k · L_KL

    L_rec    reconstruction of Y from S through gφ                      (Eq. 37)
    L_prior  GP log-density evaluated on each recovered trajectory       (Eq. 27)
    L_diff   DDPM ε-prediction on the trajectories themselves            (Eq. 40-41)
    L_KL     anchors the starting distribution against N(0, I)           (Eq. 57)

Why this is the right model for news rather than a generic autoencoder.

A topic classifier maps an article to a label from a fixed taxonomy. The mixing
map here does the opposite: given an article, it asks which combination of
latent forces, each evolving with its own temporal scale, could have generated
this observation. Two articles in different topics that share a dominant source
column expose a structural link that the taxonomy hides — a lithium supply-chain
piece and a European industrial-policy piece can both load heavily on the same
"strategic-resource competition" force even though they sit in different
sections of the news site.

The per-source GP carries the load that auxiliary variables carry in nonlinear
ICA (paper Section 2.8, Hyvärinen et al. 2019): without some non-exchangeable
structural assumption, source recovery is not identifiable. Here the
non-exchangeability comes from each source being forced to evolve at its own
characteristic timescale, learned via ℓ_k = exp(γ_k) + 10^-6 (paper Eq. 24).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class Config:
    n_sources: int = 8
    diffusion_steps: int = 20
    mixing_hidden: int = 128
    epsilon_hidden: int = 16
    epsilon_layers: int = 3
    kernel_amplitude: float = 1.0
    kernel_jitter: float = 1e-3
    lambda_prior: float = 0.1
    lambda_diff: float = 1.0
    lambda_kl: float = 0.01
    reconstruction_variance: float = 1.0
    learning_rate: float = 3e-3
    iterations: int = 1500
    mc_samples: int = 20
    seed: int = 0


def _variance_preserving_schedule(steps: int) -> torch.Tensor:
    betas = torch.linspace(1e-4, 0.02, steps)
    return torch.cumprod(1.0 - betas, dim=0)


class _EpsilonGroup(nn.Module):
    """K parallel ε-networks implemented as a single grouped 1D conv stack.

    Each source owns its own slice of the parameters via groups=K, so updates
    remain source-specific (the paper assigns a distinct ε_{θ_k} per source,
    Eq. 12). Running them as one grouped tensor is purely an efficiency choice:
    semantically equivalent to K independent networks, but one kernel call.

    The 1D conv structure (rather than a per-position MLP) is the substantive
    choice: source activations along the chronologically ordered article axis
    form a temporal signal with local structure, and we want denoising to
    exploit that locality.
    """

    def __init__(self, n_sources: int, hidden: int, layers: int):
        super().__init__()
        K, H = n_sources, hidden
        self._tau_dim = 16
        self.film = nn.Sequential(
            nn.Linear(self._tau_dim, K * H),
            nn.SiLU(),
            nn.Linear(K * H, K * H),
        )
        self.input_proj = nn.Conv1d(K, K * H, kernel_size=5, padding=2, groups=K)
        self.middle = nn.ModuleList(
            nn.Conv1d(K * H, K * H, kernel_size=5, padding=2, groups=K)
            for _ in range(layers)
        )
        self.output_proj = nn.Conv1d(K * H, K, kernel_size=5, padding=2, groups=K)

    def _embed_step(self, tau: torch.Tensor) -> torch.Tensor:
        half = self._tau_dim // 2
        freqs = torch.exp(
            -math.log(1e4) * torch.arange(half, device=tau.device, dtype=torch.float32) / half
        )
        angle = tau * freqs * 2 * math.pi
        return torch.cat([torch.sin(angle), torch.cos(angle)])

    def forward(self, trajectories: torch.Tensor, tau: torch.Tensor) -> torch.Tensor:
        shift = self.film(self._embed_step(tau)).view(1, -1, 1)
        h = self.input_proj(trajectories.unsqueeze(0))
        for conv in self.middle:
            h = F.silu(conv(h) + shift)
        return self.output_proj(h).squeeze(0)


class SourceModel(nn.Module):
    def __init__(self, n_articles: int, embedding_dim: int, config: Config):
        super().__init__()
        self.config = config
        self.N = n_articles
        self.K = config.n_sources
        self.d = embedding_dim

        # Per-source, per-article starting Gaussian (paper Eq. 7). σ is
        # parameterised as exp(log_σ) to stay positive without a softplus
        # discontinuity around zero.
        self.mu = nn.Parameter(torch.zeros(self.K, self.N))
        self.log_sigma = nn.Parameter(torch.zeros(self.K, self.N))

        # ℓ_k = exp(γ_k) + 10^-6 (paper Eq. 24). Initialised at 0.1 in
        # normalised time, i.e. one tenth of the observation window — broad
        # enough that no source starts pinned to a single article.
        self.log_length_scale = nn.Parameter(
            torch.full((self.K,), math.log(0.1))
        )

        self.epsilon = _EpsilonGroup(self.K, config.epsilon_hidden, config.epsilon_layers)

        # gφ is the non-linear instantiation from paper Section 2.1. For news,
        # the mapping from latent forces to manifest embeddings is almost
        # certainly non-linear: the same force surfaces in many writing styles
        # and framings, which a single matrix cannot capture.
        self.mixing = nn.Sequential(
            nn.Linear(self.K, config.mixing_hidden),
            nn.GELU(),
            nn.Linear(config.mixing_hidden, self.d),
        )

        self.register_buffer("alpha_bars", _variance_preserving_schedule(config.diffusion_steps))
        self.register_buffer("times", torch.zeros(self.N))

    def set_times(self, times: torch.Tensor) -> None:
        # Normalise to [0, 1]: the squared-exponential kernel is scale-sensitive
        # and the absolute scale is absorbed into ℓ_k anyway. The original
        # span is restored on output for human-readable length-scales.
        t = times.float()
        span = (t.max() - t.min()).clamp_min(1e-12)
        self.times.copy_((t - t.min()) / span)

    def _kernels(self) -> torch.Tensor:
        ell = torch.exp(self.log_length_scale) + 1e-6
        diff = self.times[:, None] - self.times[None, :]
        squared_distance = diff[None, :, :] ** 2 / (2 * ell[:, None, None] ** 2)
        cov = self.config.kernel_amplitude * torch.exp(-squared_distance)
        return cov + self.config.kernel_jitter * torch.eye(self.N, device=cov.device)

    def _sample_starts(self) -> torch.Tensor:
        return self.mu + torch.exp(self.log_sigma) * torch.randn_like(self.mu)

    def _reverse_diffusion(self, z: torch.Tensor) -> torch.Tensor:
        # DDIM-style deterministic reverse pass (paper Eq. 13-14). Each of the
        # L steps invokes the grouped ε-network once. This is the dominant
        # neural-network cost per iteration; the dominant overall cost remains
        # the Cholesky factorisation in _gp_log_density.
        x = z
        L = len(self.alpha_bars)
        for step in reversed(range(L)):
            a_bar = self.alpha_bars[step]
            tau = torch.tensor((step + 1) / L, device=z.device)
            eps_hat = self.epsilon(x, tau)
            x0_hat = (x - torch.sqrt(1 - a_bar) * eps_hat) / (torch.sqrt(a_bar) + 1e-6)
            if step == 0:
                x = x0_hat
            else:
                a_bar_prev = self.alpha_bars[step - 1]
                x = torch.sqrt(a_bar_prev) * x0_hat + torch.sqrt(1 - a_bar_prev) * eps_hat
        return x

    def forward(self) -> dict:
        z = self._sample_starts()
        s = self._reverse_diffusion(z)
        y_hat = self.mixing(s.transpose(0, 1))
        return {"sources": s, "starts": z, "reconstruction": y_hat}

    def _gp_log_density(self, s: torch.Tensor) -> torch.Tensor:
        # One Cholesky per source for both log|K| (sum of log diagonals) and
        # K^{-1} s (triangular solve). This is the per-iteration bottleneck.
        cov = self._kernels()
        chol = torch.linalg.cholesky(cov)
        log_det = 2.0 * torch.log(torch.diagonal(chol, dim1=-2, dim2=-1)).sum(-1)
        quadratic = (s * torch.cholesky_solve(s.unsqueeze(-1), chol).squeeze(-1)).sum(-1)
        return -0.5 * (self.N * math.log(2 * math.pi) + log_det + quadratic)

    def compute_losses(self, Y: torch.Tensor, outputs: dict) -> dict:
        s = outputs["sources"]
        y_hat = outputs["reconstruction"]
        cfg = self.config

        rec = ((Y - y_hat) ** 2).sum() / (2 * cfg.reconstruction_variance * self.N * self.d)
        prior = -self._gp_log_density(s).sum() / (self.N * self.K)

        # Single-step unbiased estimator of the finite-step denoising
        # objective (paper Proposition 2.3). The fresh τ and η each iteration
        # are what tie the ε-network's gradients to the actual recovered
        # trajectories, not just to externally fixed targets — this is the
        # coupling the paper insists on (last paragraph of Section 2.5).
        L = len(self.alpha_bars)
        step = int(torch.randint(0, L, (1,)).item())
        a_bar = self.alpha_bars[step]
        eta = torch.randn_like(s)
        x_tau = torch.sqrt(a_bar) * s + torch.sqrt(1 - a_bar) * eta
        eps_pred = self.epsilon(x_tau, torch.tensor((step + 1) / L, device=s.device))
        diff = ((eps_pred - eta) ** 2).mean()

        sigma_sq = torch.exp(2 * self.log_sigma)
        kl = 0.5 * (self.mu ** 2 + sigma_sq - 1.0 - 2 * self.log_sigma).mean()

        total = rec + cfg.lambda_prior * prior + cfg.lambda_diff * diff + cfg.lambda_kl * kl
        return {"total": total, "rec": rec, "prior": prior, "diff": diff, "kl": kl}

    @torch.no_grad()
    def monte_carlo_sources(self, n_samples: int) -> tuple[torch.Tensor, torch.Tensor]:
        samples = torch.stack(
            [self._reverse_diffusion(self._sample_starts()) for _ in range(n_samples)]
        )
        return samples.mean(0), samples.std(0)


def fit_sources(
    embeddings: np.ndarray,
    timestamps: np.ndarray,
    config: Config = Config(),
    device: str = "cpu",
) -> dict:
    """Fit the source-wise GP-prior model and return the recovered source matrix,
    per-source length-scales in the original time unit, and a sparse training
    history for diagnostics.

    The returned `S` has shape (N, K) — articles down rows, sources across
    columns — which is the natural orientation for downstream graph code.
    """
    torch.manual_seed(config.seed)

    Y = torch.as_tensor(embeddings, dtype=torch.float32, device=device)
    times = torch.as_tensor(timestamps, dtype=torch.float32, device=device)
    n_articles, embedding_dim = Y.shape

    model = SourceModel(n_articles, embedding_dim, config).to(device)
    model.set_times(times)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)

    history = []
    for iteration in range(config.iterations):
        optimizer.zero_grad()
        outputs = model()
        losses = model.compute_losses(Y, outputs)
        losses["total"].backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        optimizer.step()
        if iteration % 100 == 0 or iteration == config.iterations - 1:
            history.append({k: float(v) for k, v in losses.items()})

    s_mean, s_std = model.monte_carlo_sources(config.mc_samples)

    time_span = float((times.max() - times.min()).clamp_min(1e-12))
    ell_in_original_units = (torch.exp(model.log_length_scale) + 1e-6).detach().cpu().numpy() * time_span

    return {
        "S": s_mean.t().cpu().numpy(),
        "S_std": s_std.t().cpu().numpy(),
        "length_scales": ell_in_original_units,
        "history": history,
    }
