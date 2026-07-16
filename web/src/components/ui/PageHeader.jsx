import { Badge } from "@/components/ui/Badge";

export function PageHeader({ actions, badge, badgeIcon, description, title }) {
  return (
    <header className="nt-page-header">
      <div className="nt-page-header__content">
        {badge ? <Badge icon={badgeIcon}>{badge}</Badge> : null}
        <h1 className="nt-page-header__title">{title}</h1>
        {description ? <p className="nt-page-header__description">{description}</p> : null}
      </div>
      {actions ? <div className="nt-page-header__actions">{actions}</div> : null}
    </header>
  );
}
