"""
Initial data seeding script.
Run this after database migrations to populate initial data.
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.database.base import async_session_maker
from app.infrastructure.database.models import Plan, AgentTemplate, Model
from decimal import Decimal


async def seed_plans(db: AsyncSession):
    """Seed initial plans."""
    plans_data = [
        {
            "name": "入门版",
            "description": "适合个人用户，基础配置",
            "cpu": 1,
            "memory": 2048,
            "disk": 20,
            "max_agents": 1,
            "max_channels": 2,
            "price_per_month": Decimal("99.00"),
            "features": ["基础监控", "每日备份", "邮件支持"],
            "sort_order": 1
        },
        {
            "name": "标准版",
            "description": "适合小型团队，性能均衡",
            "cpu": 2,
            "memory": 4096,
            "disk": 40,
            "max_agents": 3,
            "max_channels": 5,
            "price_per_month": Decimal("199.00"),
            "features": ["高级监控", "实时备份", "优先支持", "多渠道接入"],
            "sort_order": 2
        },
        {
            "name": "专业版",
            "description": "适合中型企业，高性能配置",
            "cpu": 4,
            "memory": 8192,
            "disk": 80,
            "max_agents": 10,
            "max_channels": 20,
            "price_per_month": Decimal("399.00"),
            "features": ["企业级监控", "实时备份", "专属支持", "无限渠道", "API访问"],
            "is_popular": True,
            "sort_order": 3
        },
        {
            "name": "企业版",
            "description": "适合大型企业，顶级配置",
            "cpu": 8,
            "memory": 16384,
            "disk": 160,
            "max_agents": 50,
            "max_channels": 100,
            "price_per_month": Decimal("799.00"),
            "features": ["企业级监控", "实时备份", "24/7专属支持", "无限渠道", "API访问", "定制开发"],
            "sort_order": 4
        }
    ]
    
    for plan_data in plans_data:
        # Check if plan already exists
        result = await db.execute(select(Plan).where(Plan.name == plan_data["name"]))
        if not result.scalar_one_or_none():
            plan = Plan(**plan_data)
            db.add(plan)
    
    await db.commit()
    print("✅ Plans seeded")


async def seed_agent_templates(db: AsyncSession):
    """Seed initial agent templates."""
    templates_data = [
        {
            "name": "客服助手",
            "description": "智能客服机器人，支持多轮对话、情感分析和工单创建",
            "category": "customer_service",
            "system_prompt": "你是一个专业的客服助手，需要友好、耐心地回答用户问题。请使用简洁清晰的语言，必要时主动询问更多细节。",
            "default_config": {
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "features": ["多轮对话", "情感分析", "工单创建", "知识库查询"],
            "is_popular": True
        },
        {
            "name": "数据分析助手",
            "description": "帮助用户进行数据分析和可视化",
            "category": "data_analysis",
            "system_prompt": "你是一个数据分析专家，帮助用户理解和分析数据。提供清晰的数据洞察和建议。",
            "default_config": {
                "temperature": 0.3,
                "max_tokens": 3000
            },
            "features": ["数据清洗", "统计分析", "可视化建议", "报告生成"],
            "is_popular": True
        },
        {
            "name": "财务顾问",
            "description": "提供财务分析和投资建议",
            "category": "finance",
            "system_prompt": "你是一个专业的财务顾问，提供客观、专业的财务建议。注意：所有建议仅供参考，不构成投资建议。",
            "default_config": {
                "temperature": 0.4,
                "max_tokens": 2500
            },
            "features": ["财务分析", "风险评估", "投资建议", "预算规划"],
            "is_popular": False
        },
        {
            "name": "内容创作助手",
            "description": "帮助用户创作各类内容，包括文章、营销文案等",
            "category": "content_creation",
            "system_prompt": "你是一个创意内容创作助手，帮助用户创作高质量的内容。根据用户需求调整风格和语气。",
            "default_config": {
                "temperature": 0.8,
                "max_tokens": 4000
            },
            "features": ["文章写作", "营销文案", "社交媒体内容", "SEO优化"],
            "is_popular": True
        },
        {
            "name": "技术支持助手",
            "description": "提供技术问题诊断和解决方案",
            "category": "technical_support",
            "system_prompt": "你是一个技术支持专家，帮助用户诊断和解决技术问题。提供清晰的步骤指导。",
            "default_config": {
                "temperature": 0.3,
                "max_tokens": 3000
            },
            "features": ["问题诊断", "步骤指导", "代码示例", "最佳实践"],
            "is_popular": False
        }
    ]
    
    for template_data in templates_data:
        result = await db.execute(
            select(AgentTemplate).where(AgentTemplate.name == template_data["name"])
        )
        if not result.scalar_one_or_none():
            template = AgentTemplate(**template_data)
            db.add(template)
    
    await db.commit()
    print("✅ Agent templates seeded")


async def seed_models(db: AsyncSession):
    """Seed initial models."""
    models_data = [
        {
            "name": "GPT-4",
            "provider": "openai",
            "api_endpoint": "https://api.openai.com/v1",
            "api_key_encrypted": "",  # Will be configured by admin
            "price_per_1k_tokens": Decimal("0.01"),
            "max_tokens": 8192,
            "default_config": {
                "temperature": 0.7,
                "top_p": 1.0
            }
        },
        {
            "name": "GPT-3.5-Turbo",
            "provider": "openai",
            "api_endpoint": "https://api.openai.com/v1",
            "api_key_encrypted": "",
            "price_per_1k_tokens": Decimal("0.002"),
            "max_tokens": 4096,
            "default_config": {
                "temperature": 0.7,
                "top_p": 1.0
            }
        },
        {
            "name": "Claude-3",
            "provider": "anthropic",
            "api_endpoint": "https://api.anthropic.com/v1",
            "api_key_encrypted": "",
            "price_per_1k_tokens": Decimal("0.008"),
            "max_tokens": 100000,
            "default_config": {
                "temperature": 0.7,
                "top_p": 1.0
            }
        }
    ]
    
    for model_data in models_data:
        result = await db.execute(select(Model).where(Model.name == model_data["name"]))
        if not result.scalar_one_or_none():
            model = Model(**model_data)
            db.add(model)
    
    await db.commit()
    print("✅ Models seeded")


async def main():
    """Run all seeding functions."""
    print("🌱 Seeding initial data...")
    
    async with async_session_maker() as db:
        await seed_plans(db)
        await seed_agent_templates(db)
        await seed_models(db)
    
    print("✅ Initial data seeding complete!")


if __name__ == "__main__":
    asyncio.run(main())
