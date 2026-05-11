# CausalPulse

## Motivation: from StrADiff to the news stream

StrADiff (Wei, 2026) frames blind source separation as a generative problem in which
each latent dimension owns a private branch: its own reverse diffusion, its own
Gaussian-process prior with its own length-scale, its own anchor. The observed mixture
is then explained by a learned mixing map applied to the source-wise outputs. The
crucial point is not the use of diffusion as such — it is the **structural commitment**:
sources are not coordinates of a shared latent code, they are independent processes,
each with its own dynamics, that the model learns to disentangle while jointly
reconstructing the observations.

CausalPulse applies the same commitment to a different mixture. The news stream is
treated as an observation channel: each article is a high-dimensional snapshot of a
linear combination of unobserved causal forces — geopolitical tensions, monetary
cycles, climate dynamics, technological regime shifts. These forces evolve on
different timescales and surface in apparently unrelated coverage. Standard topic
classification flattens this: it labels what the article *is about*, not what it is
*driven by*. Two articles, one on lithium supply chains in Chile and one on
European industrial policy, can read as belonging to different topics while
being two projections of the same underlying force.

The translation is direct:

| StrADiff                                       | CausalPulse                                            |
|------------------------------------------------|--------------------------------------------------------|
| Mixed observation `Y ∈ ℝ^{T×m}`                | Article embeddings `Y ∈ ℝ^{N×d}`                       |
| Latent source matrix `S ∈ ℝ^{T×n}`             | Causal-force activations `S ∈ ℝ^{N×K}`                 |
| Source-wise GP prior with learned `ℓₖ`         | Per-force temporal smoothness, learned per force       |
| Mixing map `gφ(S)`                             | MLP decoder from forces back to embedding space        |
| Reverse diffusion `fθₖ` per source             | Per-force denoising of activation trajectories         |
| Joint end-to-end objective                     | Same: rec + GP + diff + KL, no post-processing         |

A graph node is therefore not just an article. It is an observation indexed against
`K` latent forces. A cross-domain edge with a high source-overlap weight is the
visible signature of a shared latent source — exactly the structure StrADiff is built
to recover.

## Architecture

No runtime backend. GitHub Actions runs the full pipeline every 12 hours: it fetches
news via the NewsAPI.ai SDK (cached to spare the 2k-query budget), embeds titles and
snippets with `all-MiniLM-L6-v2`, fits the source-wise GP-prior model on the resulting
embeddings, builds the cross-domain graph, and writes `data/data.json`. A static
React frontend on GitHub Pages reads that file and renders the graph with Cytoscape.js.

```
causalpulse/
├── .github/workflows/update.yml
├── scripts/
│   ├── fetch.py     # NewsAPI.ai → data/raw/*.jsonl (cached)
│   ├── embed.py     # MiniLM, cached by article URI
│   ├── sources.py   # StrADiff-style source-wise GP-prior model
│   ├── graph.py     # nodes + weighted edges (semantic + entity + source-overlap)
│   └── export.py    # orchestrator → data/data.json
├── frontend/        # Vite + React + Cytoscape, deployed to Pages
└── data/data.json   # committed, served as static asset
```

`scripts/sources.py` is the substantive contribution of this repo — it is the only
module written with paper-level commentary, because it is the only module where the
theoretical argument lives.

## Local run

```bash
pip install -r requirements.txt
export NEWSAPI_AI_KEY=...
python -m scripts.export
cd frontend && npm install && npm run dev
```

## Deploy

GitHub Actions runs `scripts.export` on cron, commits the updated `data/data.json`,
builds the frontend, and publishes to GitHub Pages. The API key lives in
`NEWSAPI_AI_KEY` repository secret.

## Reference

Wei, Y.-H. (2026). *StrADiff: A Structured Source-Wise Adaptive Diffusion Framework
for Linear and Nonlinear Blind Source Separation.* arXiv:2604.04973.
