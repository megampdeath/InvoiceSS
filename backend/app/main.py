from __future__ import annotations

import re
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.billing.routes import router as billing_router
from app.core.config import Settings, get_settings
from app.core.security import Principal, get_current_principal
from app.db.bootstrap import ensure_demo_seed, ensure_user_and_default_org
from app.db.models import Organization, OrganizationMember
from app.db.session import SessionLocal, get_db, init_db
from app.invoices.routes import router as invoice_router
from app.invoices.schemas import MeOut, OrganizationCreate

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    if settings.is_development:
        db = SessionLocal()
        try:
            ensure_demo_seed(db, settings)
        finally:
            db.close()
    yield


app = FastAPI(title="Invoice Extraction SaaS API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_BASE_URL, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/me", response_model=MeOut)
def me(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    active_org = ensure_user_and_default_org(db, principal, settings)
    user = db.get(__import__("app.db.models", fromlist=["User"]).User, principal.user_id)
    memberships = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.user_id == principal.user_id)
        .order_by(OrganizationMember.created_at.asc())
        .all()
    )
    return {
        "user": {
            "id": principal.user_id,
            "email": principal.email,
            "name": user.name if user else None,
        },
        "organizations": [
            {
                "id": membership.organization.id,
                "name": membership.organization.name,
                "slug": membership.organization.slug,
                "role": membership.role,
                "plan": membership.organization.plan,
                "subscription_status": membership.organization.subscription_status,
            }
            for membership in memberships
        ],
        "active_organization_id": active_org.id,
    }


@app.post("/api/organizations")
def create_organization(
    payload: OrganizationCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    ensure_user_and_default_org(db, principal, settings)
    slug = payload.slug or re.sub(r"[^a-z0-9]+", "-", payload.name.lower()).strip("-")
    organization = Organization(name=payload.name, slug=slug, billing_email=principal.email)
    db.add(organization)
    db.flush()
    db.add(OrganizationMember(organization_id=organization.id, user_id=principal.user_id, role="owner"))
    db.commit()
    db.refresh(organization)
    return {"id": organization.id, "name": organization.name, "slug": organization.slug}


@app.get("/api/organizations")
def list_organizations(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, str]]:
    ensure_user_and_default_org(db, principal, settings)
    memberships = db.query(OrganizationMember).filter(OrganizationMember.user_id == principal.user_id).all()
    return [
        {
            "id": membership.organization.id,
            "name": membership.organization.name,
            "slug": membership.organization.slug,
            "role": membership.role,
        }
        for membership in memberships
    ]


app.include_router(invoice_router)
app.include_router(billing_router)
