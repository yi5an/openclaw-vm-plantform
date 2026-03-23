#!/usr/bin/env python3
"""
Integration test for billing API.
This script tests the billing API with a real database connection.
Run with: python test_billing_integration.py
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.infrastructure.database.base import async_session_maker, init_db
from app.infrastructure.database.models import User, Order, TokenUsage, Agent, VM, Plan
from app.core.security import hash_password
from app.api.v1.billing import (
    get_usage_records,
    get_usage_stats,
    get_balance,
    get_orders,
    create_recharge
)
from app.api.v1.billing import RechargeRequest
from decimal import Decimal
from datetime import datetime, timedelta


async def test_billing_integration():
    """Run integration tests with real database."""
    
    print("="*60)
    print("Billing API Integration Test")
    print("="*60)
    
    try:
        # Initialize database connection
        await init_db()
        print("✅ Database initialized")
        
        async with async_session_maker() as db:
            # Create test user
            user = User(
                email="billing_integration_test@example.com",
                username="billing_integration_test",
                password_hash=hash_password("test123"),
                balance=Decimal("100.00"),
                role="user",
                status="active"
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"✅ Created test user: {user.username}")
            
            try:
                # Test 1: Get balance
                print("\n" + "="*60)
                print("Test 1: Get Balance")
                print("="*60)
                result = await get_balance(user, db)
                print(f"✅ Balance: {result['data']['balance']}")
                print(f"✅ Total recharged: {result['data']['total_recharged']}")
                print(f"✅ Total used: {result['data']['total_used']}")
                
                # Test 2: Create recharge
                print("\n" + "="*60)
                print("Test 2: Create Recharge")
                print("="*60)
                recharge_req = RechargeRequest(amount=100.0, payment_method="alipay")
                result = await create_recharge(recharge_req, user, db)
                print(f"✅ Order ID: {result['data']['order_id']}")
                print(f"✅ Amount: {result['data']['amount']}")
                print(f"✅ Balance before: {result['data']['balance_before']}")
                print(f"✅ Balance after: {result['data']['balance_after']}")
                
                # Verify balance updated
                await db.refresh(user)
                assert float(user.balance) == 200.0, "Balance not updated correctly"
                print(f"✅ User balance in DB: {user.balance}")
                
                # Test 3: Get orders
                print("\n" + "="*60)
                print("Test 3: Get Orders")
                print("="*60)
                result = await get_orders(None, None, 1, 20, user, db)
                print(f"✅ Total orders: {result['data']['total']}")
                if result['data']['items']:
                    order = result['data']['items'][0]
                    print(f"✅ Order type: {order['type']}")
                    print(f"✅ Order amount: {order['amount']}")
                    print(f"✅ Order status: {order['status']}")
                
                # Test 4: Create test data for usage
                print("\n" + "="*60)
                print("Test 4: Create Test Data")
                print("="*60)
                
                # Create plan
                plan = Plan(
                    name="Test Plan",
                    cpu=2,
                    memory=2048,
                    disk=20,
                    max_agents=5,
                    max_channels=5,
                    price_per_month=Decimal("50.00")
                )
                db.add(plan)
                await db.commit()
                await db.refresh(plan)
                print(f"✅ Created plan: {plan.name}")
                
                # Create VM
                vm = VM(
                    user_id=user.id,
                    plan_id=plan.id,
                    name="test-vm",
                    status="running",
                    cpu=2,
                    memory=2048,
                    disk=20,
                    expires_at=datetime.utcnow() + timedelta(days=30)
                )
                db.add(vm)
                await db.commit()
                await db.refresh(vm)
                print(f"✅ Created VM: {vm.name}")
                
                # Create agent
                agent = Agent(
                    vm_id=vm.id,
                    name="test-agent",
                    status="running",
                    model_config={"provider": "platform", "model_name": "gpt-4"}
                )
                db.add(agent)
                await db.commit()
                await db.refresh(agent)
                print(f"✅ Created agent: {agent.name}")
                
                # Create token usage
                usage = TokenUsage(
                    agent_id=agent.id,
                    vm_id=vm.id,
                    user_id=user.id,
                    model="gpt-4",
                    prompt_tokens=1000,
                    completion_tokens=500,
                    total_tokens=1500,
                    cost=Decimal("0.15")
                )
                db.add(usage)
                await db.commit()
                await db.refresh(usage)
                print(f"✅ Created token usage: {usage.total_tokens} tokens")
                
                # Test 5: Get usage records
                print("\n" + "="*60)
                print("Test 5: Get Usage Records")
                print("="*60)
                result = await get_usage_records(
                    None, None, None, 1, 20, user, db
                )
                print(f"✅ Total records: {result['data']['total']}")
                if result['data']['items']:
                    record = result['data']['items'][0]
                    print(f"✅ Model: {record['model']}")
                    print(f"✅ Tokens: {record['total_tokens']}")
                    print(f"✅ Cost: {record['cost']}")
                
                # Test 6: Get usage stats
                print("\n" + "="*60)
                print("Test 6: Get Usage Stats")
                print("="*60)
                result = await get_usage_stats("month", user, db)
                stats = result['data']
                print(f"✅ Total tokens: {stats['total_tokens']}")
                print(f"✅ Total cost: {stats['total_cost']}")
                print(f"✅ By model count: {len(stats['by_model'])}")
                if stats['by_model']:
                    print(f"✅ Top model: {stats['by_model'][0]['model']}")
                
                print("\n" + "="*60)
                print("✅ ALL TESTS PASSED!")
                print("="*60)
                
            finally:
                # Clean up test user
                await db.delete(user)
                await db.commit()
                print("\n✅ Cleaned up test data")
                
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_billing_integration())
