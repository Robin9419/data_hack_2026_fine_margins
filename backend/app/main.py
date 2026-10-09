"""Hockey Performance Cards API.

Run from the backend folder:  uvicorn app.main:app --reload
"""

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import db
from .content import get_content

app = FastAPI(title="Hockey Performance Cards")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    db.init_db()
    get_content()  # fail fast if the content or CSV is broken


def _token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not signed in")
    return authorization.removeprefix("Bearer ")


def current_user(authorization: str | None = Header(default=None)) -> dict:
    user = db.user_for_token(_token(authorization))
    if not user:
        raise HTTPException(401, "Session expired")
    return user


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=40)


@app.post("/api/login")
def login(body: LoginRequest):
    """Dummy sign-in: any username works. New users get the starter pack."""
    content = get_content()
    user, created = db.get_or_create_user(body.username.strip(), content.starter_card_ids)
    token = db.create_session(user["id"])
    return {
        "token": token,
        "user": user,
        "new_user": created,
        "starter_card_ids": content.starter_card_ids if created else [],
    }


@app.post("/api/logout")
def logout(authorization: str | None = Header(default=None)):
    db.delete_session(_token(authorization))
    return {"ok": True}


@app.get("/api/me")
def me(user: dict = Depends(current_user)):
    content = get_content()
    owned = db.owned_cards(user["id"])
    return {"user": user, "owned_count": len(owned), "total_cards": len(content.cards)}


@app.get("/api/cards")
def list_cards(user: dict = Depends(current_user)):
    """All cards in the set. Owned cards are full; locked cards only show a teaser."""
    content = get_content()
    owned = db.owned_cards(user["id"])
    result = []
    for card_id, card in content.cards.items():
        if card_id in owned:
            result.append({**card, "owned": True, "edition": owned[card_id]})
        else:
            result.append({**content.card_summary(card), "owned": False})
    return {"cards": result}


@app.get("/api/cards/{card_id}")
def get_card(card_id: str, user: dict = Depends(current_user)):
    content = get_content()
    card = content.cards.get(card_id)
    if not card:
        raise HTTPException(404, "Card not found")
    owned = db.owned_cards(user["id"])
    if card_id not in owned:
        raise HTTPException(403, "You don't own this card yet")
    return {**card, "owned": True, "edition": owned[card_id]}


@app.get("/api/metrics")
def list_metrics():
    return {"metrics": list(get_content().metrics.values())}


@app.post("/api/reset")
def reset(user: dict = Depends(current_user)):
    """Restore the user's collection to the starter pack (for demos/testing)."""
    db.reset_cards(user["id"], get_content().starter_card_ids)
    return {"ok": True}
