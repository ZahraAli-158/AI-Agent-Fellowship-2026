export default function Panel({ title, subtitle, right, icon: Icon, children, className = "" }) {
  return (
    <div className={`panel fade-in ${className}`}>
      {(title || right) && (
        <div className="panel-header">
          <div>
            {title && (
              <h3 className="panel-title">
                {Icon && <Icon size={15} style={{ color: "var(--accent)" }} />}
                {title}
              </h3>
            )}
            {subtitle && <p className="panel-subtitle">{subtitle}</p>}
          </div>
          {right}
        </div>
      )}
      <div className="panel-body">{children}</div>
    </div>
  );
}
