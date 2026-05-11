interface MobileWarningProps {
  onDismiss: () => void;
}

export function MobileWarning({ onDismiss }: MobileWarningProps) {
  return (
    <div className="mobile-warning-overlay">
      <div className="mobile-warning-content">
        <h2>Desktop Recommended</h2>
        <p>
          CausalPulse is optimized for desktop viewing. The graph visualization and interactive features work best on a larger screen.
        </p>
        <p>
          For the best experience, please open this site on a computer.
        </p>
        <button className="warning-button" onClick={onDismiss}>
          Continue on Mobile
        </button>
      </div>
    </div>
  );
}
