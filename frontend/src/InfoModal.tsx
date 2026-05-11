interface InfoModalProps {
  open: boolean;
  onClose: () => void;
}

export function InfoModal({ open, onClose }: InfoModalProps) {
  if (!open) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>✕</button>

        <div className="modal-body">
          <h2>About CausalPulse</h2>

          <p>
            The global news stream is a mixed signal, thousands of events from disconnected domains colliding in real time.
            CausalPulse treats it as a blind source separation problem: beneath the surface of observable articles lie a small
            number of latent forces (geopolitical tension, economic cycles, social dynamics) that generate what we read. The
            system learns to decompose this mixture, tracing how a single latent force propagates across domains that appear
            unrelated at first glance.
          </p>

          <p>
            The approach is directly inspired by <strong>StrADiff</strong>, a structured source-wise diffusion framework for
            signal separation. Here, each article receives an activation vector over K latent forces, not topic labels assigned
            by an editor, but emergent dimensions learned from the structure of the data itself. Edges in the graph carry weight
            not just from semantic similarity, but from shared latent force signatures, revealing cross-domain connections a
            keyword search would never surface.
          </p>

          <div className="modal-footer">
            <span>Based on</span>
            <a href="https://arxiv.org/abs/2604.04973" target="_blank" rel="noopener noreferrer">
              StrADiff (arXiv 2604.04973)
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
