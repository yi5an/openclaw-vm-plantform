"""
Test cases for Agent management API endpoints.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.models import User, VM, Plan, Agent, AgentStatus
from app.core.security import get_password_hash, create_token
from datetime import datetime, timedelta


@pytest.fixture
async def test_user(db: AsyncSession):
    """Create a test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        password_hash=get_password_hash("testpass123"),
        balance=100.00
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def test_plan(db: AsyncSession):
    """Create a test plan."""
    plan = Plan(
        name="Basic Plan",
        description="Test plan",
        cpu=2,
        memory=4096,
        disk=50,
        max_agents=5,
        max_channels=3,
        price_per_month=29.99,
        features=["Feature 1", "Feature 2"]
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@pytest.fixture
async def test_vm(db: AsyncSession, test_user: User, test_plan: Plan):
    """Create a test VM."""
    vm = VM(
        user_id=test_user.id,
        plan_id=test_plan.id,
        name="Test VM",
        status="running",
        cpu=2,
        memory=4096,
        disk=50,
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    db.add(vm)
    await db.commit()
    await db.refresh(vm)
    return vm


@pytest.fixture
def auth_headers(test_user: User):
    """Create authentication headers."""
    token = create_token({"sub": str(test_user.id), "type": "access"})
    return {"Authorization": f"Bearer {token}"}


class TestCreateAgent:
    """Test cases for creating agents."""
    
    @pytest.mark.asyncio
    async def test_create_agent_success(
        self,
        client: AsyncClient,
        test_vm: VM,
        auth_headers: dict
    ):
        """Test successful agent creation."""
        response = await client.post(
            "/api/v1/agents",
            json={
                "vm_id": str(test_vm.id),
                "name": "Test Agent",
                "system_prompt": "You are a helpful assistant",
                "model_config": {
                    "provider": "platform",
                    "model_name": "gpt-4",
                    "temperature": 0.7
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Test Agent"
        assert data["data"]["status"] == "creating"
    
    @pytest.mark.asyncio
    async def test_create_agent_with_custom_provider(
        self,
        client: AsyncClient,
        test_vm: VM,
        auth_headers: dict
    ):
        """Test creating agent with custom provider."""
        response = await client.post(
            "/api/v1/agents",
            json={
                "vm_id": str(test_vm.id),
                "name": "Custom Agent",
                "system_prompt": "Custom assistant",
                "model_config": {
                    "provider": "custom",
                    "model_name": "gpt-4",
                    "api_key": "sk-test123",
                    "temperature": 0.8
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_create_agent_custom_without_api_key(
        self,
        client: AsyncClient,
        test_vm: VM,
        auth_headers: dict
    ):
        """Test creating agent with custom provider but no API key."""
        response = await client.post(
            "/api/v1/agents",
            json={
                "vm_id": str(test_vm.id),
                "name": "Bad Agent",
                "system_prompt": "Test",
                "model_config": {
                    "provider": "custom",
                    "model_name": "gpt-4",
                    "temperature": 0.7
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_create_agent_unauthorized_vm(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db: AsyncSession
    ):
        """Test creating agent for VM owned by another user."""
        # Create another user's VM
        other_user = User(
            email="other@example.com",
            username="otheruser",
            password_hash=get_password_hash("pass123")
        )
        db.add(other_user)
        await db.commit()
        await db.refresh(other_user)
        
        plan = Plan(
            name="Plan",
            cpu=1,
            memory=2048,
            disk=20,
            max_agents=3,
            max_channels=2,
            price_per_month=19.99
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        
        vm = VM(
            user_id=other_user.id,
            plan_id=plan.id,
            name="Other VM",
            status="running",
            cpu=1,
            memory=2048,
            disk=20,
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db.add(vm)
        await db.commit()
        await db.refresh(vm)
        
        response = await client.post(
            "/api/v1/agents",
            json={
                "vm_id": str(vm.id),
                "name": "Test Agent",
                "system_prompt": "Test",
                "model_config": {
                    "provider": "platform",
                    "model_name": "gpt-4",
                    "temperature": 0.7
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_create_agent_quota_exceeded(
        self,
        client: AsyncClient,
        test_vm: VM,
        auth_headers: dict,
        db: AsyncSession
    ):
        """Test creating agent when quota is exceeded."""
        # Get plan to know max_agents
        from sqlalchemy import select
        result = await db.execute(select(Plan).where(Plan.id == test_vm.plan_id))
        plan = result.scalar_one()
        
        # Create max_agents number of agents
        for i in range(plan.max_agents):
            agent = Agent(
                vm_id=test_vm.id,
                name=f"Agent {i}",
                status=AgentStatus.STOPPED,
                system_prompt="Test",
                model_config={"provider": "platform", "model_name": "gpt-4"}
            )
            db.add(agent)
        await db.commit()
        
        # Try to create one more
        response = await client.post(
            "/api/v1/agents",
            json={
                "vm_id": str(test_vm.id),
                "name": "Excess Agent",
                "system_prompt": "Test",
                "model_config": {
                    "provider": "platform",
                    "model_name": "gpt-4",
                    "temperature": 0.7
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 400


class TestListAgents:
    """Test cases for listing agents."""
    
    @pytest.mark.asyncio
    async def test_list_agents_success(
        self,
        client: AsyncClient,
        test_vm: VM,
        auth_headers: dict,
        db: AsyncSession
    ):
        """Test listing agents."""
        # Create some agents
        for i in range(3):
            agent = Agent(
                vm_id=test_vm.id,
                name=f"Agent {i}",
                status=AgentStatus.RUNNING,
                system_prompt=f"Prompt {i}",
                model_config={"provider": "platform", "model_name": "gpt-4"}
            )
            db.add(agent)
        await db.commit()
        
        response = await client.get(
            "/api/v1/agents",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["items"]) == 3
    
    @pytest.mark.asyncio
    async def test_list_agents_by_vm(
        self,
        client: AsyncClient,
        test_vm: VM,
        test_user: User,
        test_plan: Plan,
        auth_headers: dict,
        db: AsyncSession
    ):
        """Test listing agents filtered by VM."""
        # Create another VM
        vm2 = VM(
            user_id=test_user.id,
            plan_id=test_plan.id,
            name="VM 2",
            status="running",
            cpu=2,
            memory=4096,
            disk=50,
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db.add(vm2)
        await db.commit()
        await db.refresh(vm2)
        
        # Create agents in both VMs
        for i in range(2):
            agent1 = Agent(
                vm_id=test_vm.id,
                name=f"VM1 Agent {i}",
                status=AgentStatus.RUNNING,
                system_prompt="Test",
                model_config={"provider": "platform", "model_name": "gpt-4"}
            )
            agent2 = Agent(
                vm_id=vm2.id,
                name=f"VM2 Agent {i}",
                status=AgentStatus.RUNNING,
                system_prompt="Test",
                model_config={"provider": "platform", "model_name": "gpt-4"}
            )
            db.add_all([agent1, agent2])
        await db.commit()
        
        # Filter by VM1
        response = await client.get(
            f"/api/v1/agents?vm_id={test_vm.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["items"]) == 2


class TestGetAgent:
    """Test cases for getting agent details."""
    
    @pytest.mark.asyncio
    async def test_get_agent_success(
        self,
        client: AsyncClient,
        test_vm: VM,
        auth_headers: dict,
        db: AsyncSession
    ):
        """Test getting agent details."""
        agent = Agent(
            vm_id=test_vm.id,
            name="Test Agent",
            status=AgentStatus.RUNNING,
            system_prompt="Test prompt",
            model_config={"provider": "platform", "model_name": "gpt-4"}
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        
        response = await client.get(
            f"/api/v1/agents/{agent.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Test Agent"
    
    @pytest.mark.asyncio
    async def test_get_agent_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test getting non-existent agent."""
        response = await client.get(
            "/api/v1/agents/00000000-0000-0000-0000-000000000000",
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestUpdateAgent:
    """Test cases for updating agents."""
    
    @pytest.mark.asyncio
    async def test_update_agent_name(
        self,
        client: AsyncClient,
        test_vm: VM,
        auth_headers: dict,
        db: AsyncSession
    ):
        """Test updating agent name."""
        agent = Agent(
            vm_id=test_vm.id,
            name="Old Name",
            status=AgentStatus.STOPPED,
            system_prompt="Test",
            model_config={"provider": "platform", "model_name": "gpt-4"}
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        
        response = await client.patch(
            f"/api/v1/agents/{agent.id}",
            json={"name": "New Name"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "New Name"
    
    @pytest.mark.asyncio
    async def test_update_agent_system_prompt(
        self,
        client: AsyncClient,
        test_vm: VM,
        auth_headers: dict,
        db: AsyncSession
    ):
        """Test updating agent system prompt."""
        agent = Agent(
            vm_id=test_vm.id,
            name="Test Agent",
            status=AgentStatus.STOPPED,
            system_prompt="Old prompt",
            model_config={"provider": "platform", "model_name": "gpt-4"}
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        
        response = await client.patch(
            f"/api/v1/agents/{agent.id}",
            json={"system_prompt": "New prompt"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["system_prompt"] == "New prompt"


class TestStartAgent:
    """Test cases for starting agents."""
    
    @pytest.mark.asyncio
    async def test_start_agent_success(
        self,
        client: AsyncClient,
        test_vm: VM,
        auth_headers: dict,
        db: AsyncSession
    ):
        """Test starting a stopped agent."""
        agent = Agent(
            vm_id=test_vm.id,
            name="Test Agent",
            status=AgentStatus.STOPPED,
            system_prompt="Test",
            model_config={"provider": "platform", "model_name": "gpt-4"}
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        
        response = await client.post(
            f"/api/v1/agents/{agent.id}/start",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_start_already_running_agent(
        self,
        client: AsyncClient,
        test_vm: VM,
        auth_headers: dict,
        db: AsyncSession
    ):
        """Test starting an already running agent."""
        agent = Agent(
            vm_id=test_vm.id,
            name="Test Agent",
            status=AgentStatus.RUNNING,
            system_prompt="Test",
            model_config={"provider": "platform", "model_name": "gpt-4"}
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        
        response = await client.post(
            f"/api/v1/agents/{agent.id}/start",
            headers=auth_headers
        )
        
        assert response.status_code == 400


class TestStopAgent:
    """Test cases for stopping agents."""
    
    @pytest.mark.asyncio
    async def test_stop_agent_success(
        self,
        client: AsyncClient,
        test_vm: VM,
        auth_headers: dict,
        db: AsyncSession
    ):
        """Test stopping a running agent."""
        agent = Agent(
            vm_id=test_vm.id,
            name="Test Agent",
            status=AgentStatus.RUNNING,
            system_prompt="Test",
            model_config={"provider": "platform", "model_name": "gpt-4"}
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        
        response = await client.post(
            f"/api/v1/agents/{agent.id}/stop",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "stopped"
    
    @pytest.mark.asyncio
    async def test_stop_already_stopped_agent(
        self,
        client: AsyncClient,
        test_vm: VM,
        auth_headers: dict,
        db: AsyncSession
    ):
        """Test stopping an already stopped agent."""
        agent = Agent(
            vm_id=test_vm.id,
            name="Test Agent",
            status=AgentStatus.STOPPED,
            system_prompt="Test",
            model_config={"provider": "platform", "model_name": "gpt-4"}
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        
        response = await client.post(
            f"/api/v1/agents/{agent.id}/stop",
            headers=auth_headers
        )
        
        assert response.status_code == 400


class TestDeleteAgent:
    """Test cases for deleting agents."""
    
    @pytest.mark.asyncio
    async def test_delete_agent_success(
        self,
        client: AsyncClient,
        test_vm: VM,
        auth_headers: dict,
        db: AsyncSession
    ):
        """Test deleting a stopped agent."""
        agent = Agent(
            vm_id=test_vm.id,
            name="Test Agent",
            status=AgentStatus.STOPPED,
            system_prompt="Test",
            model_config={"provider": "platform", "model_name": "gpt-4"}
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        agent_id = str(agent.id)
        
        response = await client.delete(
            f"/api/v1/agents/{agent_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify deleted
        from sqlalchemy import select
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        assert result.scalar_one_or_none() is None
    
    @pytest.mark.asyncio
    async def test_delete_running_agent(
        self,
        client: AsyncClient,
        test_vm: VM,
        auth_headers: dict,
        db: AsyncSession
    ):
        """Test deleting a running agent."""
        agent = Agent(
            vm_id=test_vm.id,
            name="Test Agent",
            status=AgentStatus.RUNNING,
            system_prompt="Test",
            model_config={"provider": "platform", "model_name": "gpt-4"}
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        
        response = await client.delete(
            f"/api/v1/agents/{agent.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 400


class TestValidateToken:
    """Test cases for token validation."""
    
    @pytest.mark.asyncio
    async def test_validate_token_success(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test token validation."""
        response = await client.post(
            "/api/v1/agents/validate-token",
            json={
                "provider": "openai",
                "api_key": "sk-test123456789",
                "model_name": "gpt-4"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["valid"] is True
    
    @pytest.mark.asyncio
    async def test_validate_invalid_token_format(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test validating token with invalid format."""
        response = await client.post(
            "/api/v1/agents/validate-token",
            json={
                "provider": "openai",
                "api_key": "invalid",
                "model_name": "gpt-4"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 400
