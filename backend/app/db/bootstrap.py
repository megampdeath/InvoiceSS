from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import Principal
from app.db.models import Organization, OrganizationMember, User


def ensure_user_and_default_org(db: Session, principal: Principal, settings: Settings) -> Organization:
    user = db.get(User, principal.user_id)
    if user is None:
        user = User(
            id=principal.user_id,
            email=principal.email,
            name=principal.email.split("@", 1)[0],
            auth_provider="supabase" if settings.SUPABASE_URL else "demo",
        )
        db.add(user)

    membership = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.user_id == principal.user_id)
        .order_by(OrganizationMember.created_at.asc())
        .first()
    )
    if membership:
        db.flush()
        return membership.organization

    organization_id = settings.DEMO_ORGANIZATION_ID if principal.user_id == settings.DEMO_USER_ID else None
    organization = Organization(
        id=organization_id,
        name="Demo Workspace" if organization_id else f"{user.name or 'My'} Workspace",
        slug="demo-workspace" if organization_id else f"workspace-{principal.user_id[:8]}",
        billing_email=principal.email,
        plan="free",
        subscription_status="free",
        usage_period_start=date.today().replace(day=1),
        usage_period_end=date.today().replace(day=28) + timedelta(days=4),
    )
    organization.usage_period_end = organization.usage_period_end.replace(day=1) - timedelta(days=1)
    db.add(organization)
    db.flush()
    db.add(
        OrganizationMember(
            organization_id=organization.id,
            user_id=user.id,
            role="owner",
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    db.refresh(organization)
    return organization


def ensure_demo_seed(db: Session, settings: Settings) -> None:
    principal = Principal(user_id=settings.DEMO_USER_ID, email=settings.DEMO_USER_EMAIL)
    ensure_user_and_default_org(db, principal, settings)
