"""
Manual test script for billing API.
This script tests the billing API endpoints without pytest.
"""
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.infrastructure.database.models import (
    Base, User, Order, TokenUsage, Agent, VM, Plan,
    OrderType, OrderStatus, UserRole, UserStatus, VMStatus, AgentStatus
)
from app.core.security import hash_password


async def test_billing_apis():
    """Test billing API functions manually."""
    
    # Create in-memory database
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session_maker = async_sessionmaker(
        engine,
        expire_on_commit=False
    )
    
    async with async_session_maker() as db:
        # Create test user
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash=hash_password("test123"),
            balance=Decimal("100.00"),
            role=UserRole.USER,
            status=UserStatus.ACTIVE
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"✅ Created user: {user.username}, balance: {user.balance}")
        
        # Create plan
        plan = Plan(
            name="Test Plan",
            description="Test",
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
            status=VMStatus.RUNNING,
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
            status=AgentStatus.RUNNING,
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
        print(f"✅ Created token usage: {usage.total_tokens} tokens, cost: {usage.cost}")
        
        # Create order
        order = Order(
            user_id=user.id,
            type=OrderType.RECHARGE,
            amount=Decimal("50.00"),
            balance_before=Decimal("50.00"),
            balance_after=Decimal("100.00"),
            description="Test recharge",
            status=OrderStatus.COMPLETED,
            payment_method="alipay"
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)
        print(f"✅ Created order: {order.type.value}, amount: {order.amount}")
        
        print("\n" + "="*50)
        print("Testing API functions...")
        print("="*50)
        
        # Import billing functions
        from app.api.v1.billing import (
            get_usage_records,
            get_usage_stats,
            get_balance,
            get_orders,
            create_recharge
        )
        from app.api.v1.billing import RechargeRequest
        from app.api.deps import get_current_active_user
        
        # Test 1: Get usage records
        print("\n📊 Test 1: Get usage records")
        try:
            # Mock the dependency injection
            result = await get_usage_records(
                start_date=None,
                end_date=None,
                agent_id=None,
                page=1,
                page_size=20,
                current_user=user,
                db=db
            )
            print(f"   Total records: {result['data']['total']}")
            print(f"   Items: {len(result['data']['items'])}")
            if result['data']['items']:
                item = result['data']['items'][0]
                print(f"   Model: {item['model']}, Tokens: {item['total_tokens']}, Cost: {item['cost']}")
            print("   ✅ PASSED")
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
        
        # Test 2: Get usage stats
        print("\n📊 Test 2: Get usage stats")
        try:
            result = await get_usage_stats(
                period="month",
                current_user=user,
                db=db
            )
            stats = result['data']
            print(f"   Total tokens: {stats['total_tokens']}")
            print(f"   Total cost: {stats['total_cost']}")
            print(f"   By model count: {len(stats['by_model'])}")
            print("   ✅ PASSED")
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
        
        # Test 3: Get balance
        print("\n📊 Test 3: Get balance")
        try:
            result = await get_balance(
                current_user=user,
                db=db
            )
            balance_data = result['data']
            print(f"   Balance: {balance_data['balance']}")
            print(f"   Total recharged: {balance_data['total_recharged']}")
            print(f"   Total used: {balance_data['total_used']}")
            print("   ✅ PASSED")
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
        
        # Test 4: Get orders
        print("\n📊 Test 4: Get orders")
        try:
            result = await get_orders(
                order_type=None,
                status=None,
                page=1,
                page_size=20,
                current_user=user,
                db=db
            )
            print(f"   Total orders: {result['data']['total']}")
            if result['data']['items']:
                order_item = result['data']['items'][0]
                print(f"   Order type: {order_item['type']}, Amount: {order_item['amount']}")
            print("   ✅ PASSED")
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
        
        # Test 5: Create recharge
        print("\n📊 Test 5: Create recharge")
        try:
            recharge_req = RechargeRequest(
                amount=100.0,
                payment_method="alipay"
            )
            result = await create_recharge(
                request=recharge_req,
                current_user=user,
                db=db
            )
            recharge_data = result['data']
            print(f"   Order ID: {recharge_data['order_id']}")
            print(f"   Amount: {recharge_data['amount']}")
            print(f"   Balance before: {recharge_data['balance_before']}")
            print(f"   Balance after: {recharge_data['balance_after']}")
            print(f"   Status: {recharge_data['status']}")
            
            # Verify user balance updated
            await db.refresh(user)
            print(f"   User balance in DB: {user.balance}")
            print("   ✅ PASSED")
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    # Clean up
    await engine.dispose()
    print("\n" + "="*50)
    print("✅ All manual tests completed!")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(test_billing_apis())
