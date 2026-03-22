"""
Seed initial data for the database.
"""
from app.infrastructure.database.models import Plan
from app.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create sync engine
engine = create_engine(settings.DATABASE_URL.replace("+asyncpg", ""))
Session = sessionmaker(bind=engine)

def seed_plans():
    """Create initial plan data."""
    plans = [
        {
            "name": "入门版",
            "description": "适合个人用户，包含1个Agent",
            "cpu": 1,
            "memory": 2048,
            "disk": 20,
            "max_agents": 1,
            "max_channels": 2,
            "price_per_month": 99.00,
            "features": ["1个 Agent", "2个渠道", "20GB 存储"]
        },
        {
            "name": "标准版",
            "description": "适合小型团队，包含3个Agent",
            "cpu": 2,
            "memory": 4096,
            "disk": 40,
            "max_agents": 3,
            "max_channels": 5,
            "price_per_month": 199.00,
            "features": ["3个 Agent", "5个渠道", "40GB 存储"]
        },
        {
            "name": "专业版",
            "description": "适合企业用户，包含5个Agent",
            "cpu": 4,
            "memory": 8192,
            "disk": 80,
            "max_agents": 5,
            "max_channels": 10,
            "price_per_month": 399.00,
            "features": ["5个 Agent", "10个渠道", "80GB 存储", "优先支持"]
        }
    ]
    
    session = Session()
    for plan_data in plans:
        plan = Plan(**plan_data)
        session.add(plan)
        print(f"✅ Created plan: {plan.name}")
    
    session.commit()
    print("✅ Seeded 3 plans successfully!")

if __name__ == "__main__":
    seed_plans()
