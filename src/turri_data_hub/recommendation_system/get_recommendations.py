from sqlalchemy.orm import selectinload
from sqlmodel import select

from src.turri_data_hub.db import TurriDB

from ..woocommerce.models import Producer, Product
from .models import UserBehavior

CATEGORIES_FACTOR = 4
EMBEDDINGS_FACTOR = 1


async def _hybrid_top_k(
    db: TurriDB,
    user: UserBehavior,
    k: int,
    model,
    taste_embedding_attr: str = "taste_embedding",
    embedding_attr: str = "embedding",
):
    """
    Generic hybrid search for a model with taste_embedding and embedding.
    """
    async with db.session_maker() as session:
        # Taste embedding distance
        taste_stmt = (
            select(
                model,
                getattr(model, taste_embedding_attr)
                .l2_distance(user.taste_embedding)
                .label("taste_score"),
            )
            .order_by(
                getattr(model, taste_embedding_attr).l2_distance(user.taste_embedding)
            )
            .limit(k * 3)
        )
        taste_results = await session.execute(taste_stmt)
        taste_scores = {
            getattr(row, model.__name__).id: getattr(row, "taste_score")
            for row in taste_results.fetchall()
        }

        # Embedding distance
        emb_stmt = (
            select(
                model,
                getattr(model, embedding_attr)
                .l2_distance(user.embedding)
                .label("emb_score"),
            )
            .order_by(getattr(model, embedding_attr).l2_distance(user.embedding))
            .limit(k * 3)
        )
        emb_results = await session.execute(emb_stmt)
        emb_scores = {
            getattr(row, model.__name__).id: getattr(row, "emb_score")
            for row in emb_results.fetchall()
        }

        # Merge and score
        all_ids = set(taste_scores) | set(emb_scores)
        scored = []
        for pid in all_ids:
            taste = taste_scores.get(pid, 1000)
            emb = emb_scores.get(pid, 1000)
            score = CATEGORIES_FACTOR * taste + EMBEDDINGS_FACTOR * emb
            scored.append((pid, score))

        scored.sort(key=lambda x: x[1])
        top_ids = [pid for pid, _ in scored[:k]]
        if not top_ids:
            return []
        # Use selectinload for Product.producer if model is Product
        stmt = select(model).where(model.id.in_(top_ids))
        if model is Product:
            stmt = stmt.options(selectinload(Product.producer))
        objs = await session.execute(stmt)
        id_to_obj = {o.id: o for o in objs.scalars().all()}
        return [id_to_obj[pid] for pid in top_ids if pid in id_to_obj]


async def get_top_k_products(db: TurriDB, user: UserBehavior, k: int) -> list[Product]:
    """
    Hybrid search: combine taste_embedding and embedding similarity for products.
    """
    return await _hybrid_top_k(db, user, k, Product)


async def get_top_k_producers(
    db: TurriDB, user: UserBehavior, k: int
) -> list[Producer]:
    """
    Hybrid search: combine taste_embedding and embedding similarity for producers.
    """
    return await _hybrid_top_k(db, user, k, Producer)
