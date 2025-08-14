# Contributing Guide

Thank you for considering contributing to Kasa Monitor! This guide will help you get started with contributing to the project.

## How to Contribute

```
┌─────────────────────────────────────┐
│     Contribution Workflow           │
├─────────────────────────────────────┤
│  1. Fork Repository                 │
│  2. Create Feature Branch           │
│  3. Make Changes                    │
│  4. Test Thoroughly                 │
│  5. Submit Pull Request             │
└─────────────────────────────────────┘
```

## Getting Started

### Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/kasa-monitor.git
cd kasa-monitor

# Add upstream remote
git remote add upstream https://github.com/xante8088/kasa-monitor.git

# Keep your fork updated
git fetch upstream
git checkout main
git merge upstream/main
```

### Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install frontend dependencies
cd frontend
npm install
cd ..

# Set up pre-commit hooks
pre-commit install
```

### Environment Configuration

```bash
# Copy example environment file
cp .env.example .env.development

# Edit with your settings
nano .env.development
```

## Development Workflow

### Creating a Feature Branch

```bash
# Create and checkout new branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description

# Or for documentation
git checkout -b docs/update-description
```

### Branch Naming Convention

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/updates
- `chore/` - Maintenance tasks

### Making Changes

#### Code Style

**Python (Backend):**
```python
# Follow PEP 8
# Use type hints
from typing import List, Optional

async def get_devices(
    limit: int = 100,
    offset: int = 0
) -> List[dict]:
    """
    Get list of devices.
    
    Args:
        limit: Maximum number of devices to return
        offset: Number of devices to skip
        
    Returns:
        List of device dictionaries
    """
    # Implementation
    pass

# Use descriptive variable names
device_power_consumption = calculate_power()  # Good
pwr = calc()  # Bad

# Constants in UPPER_CASE
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT = 30
```

**TypeScript/JavaScript (Frontend):**
```typescript
// Use TypeScript for type safety
interface Device {
  deviceIp: string;
  deviceName: string;
  isActive: boolean;
  powerW?: number;
}

// Use async/await over promises
const fetchDevices = async (): Promise<Device[]> => {
  try {
    const response = await fetch('/api/devices');
    return await response.json();
  } catch (error) {
    console.error('Failed to fetch devices:', error);
    throw error;
  }
};

// Use meaningful component names
const DeviceStatusIndicator: React.FC<{device: Device}> = ({ device }) => {
  // Component implementation
};
```

#### Commit Messages

Follow conventional commits format:

```bash
# Format: <type>(<scope>): <subject>

# Examples:
git commit -m "feat(devices): add manual device entry"
git commit -m "fix(auth): resolve login redirect loop"
git commit -m "docs(api): update endpoint documentation"
git commit -m "style(frontend): improve dashboard layout"
git commit -m "refactor(polling): optimize device polling logic"
git commit -m "test(energy): add energy calculation tests"
git commit -m "chore(deps): update dependencies"
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting, missing semicolons, etc.
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

### Testing

#### Running Tests

```bash
# Backend tests
pytest tests/
pytest tests/ -v  # Verbose output
pytest tests/ --cov=backend  # With coverage

# Frontend tests
npm test
npm run test:coverage

# E2E tests
npm run test:e2e

# Linting
flake8 backend/
black backend/ --check
npm run lint
```

#### Writing Tests

**Python Test Example:**
```python
# tests/test_device_manager.py
import pytest
from unittest.mock import Mock, patch
from backend.device_manager import DeviceManager

@pytest.fixture
def device_manager():
    return DeviceManager()

@pytest.fixture
def mock_device():
    return {
        'device_ip': '192.168.1.100',
        'device_name': 'Test Device',
        'is_active': True
    }

async def test_add_device(device_manager, mock_device):
    """Test adding a new device."""
    result = await device_manager.add_device(mock_device)
    assert result['device_ip'] == mock_device['device_ip']
    assert result['success'] is True

async def test_device_discovery_timeout():
    """Test discovery timeout handling."""
    with patch('backend.device_manager.discover') as mock_discover:
        mock_discover.side_effect = TimeoutError()
        
        manager = DeviceManager()
        result = await manager.discover_devices()
        
        assert result == []
        assert manager.last_error == "Discovery timeout"
```

**React Test Example:**
```typescript
// tests/DeviceCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { DeviceCard } from '../src/components/DeviceCard';

describe('DeviceCard', () => {
  const mockDevice = {
    deviceIp: '192.168.1.100',
    deviceName: 'Living Room',
    isActive: true,
    powerW: 50.5
  };

  it('renders device information', () => {
    render(<DeviceCard device={mockDevice} />);
    
    expect(screen.getByText('Living Room')).toBeInTheDocument();
    expect(screen.getByText('50.5W')).toBeInTheDocument();
  });

  it('handles toggle action', async () => {
    const onToggle = jest.fn();
    render(<DeviceCard device={mockDevice} onToggle={onToggle} />);
    
    const toggleButton = screen.getByRole('button', { name: /toggle/i });
    fireEvent.click(toggleButton);
    
    expect(onToggle).toHaveBeenCalledWith('192.168.1.100');
  });
});
```

### Documentation

#### Code Documentation

```python
# Use docstrings for all public functions/classes
def calculate_energy_cost(
    kwh: float,
    rate: float,
    tax_rate: float = 0.0
) -> float:
    """
    Calculate energy cost including taxes.
    
    Args:
        kwh: Energy consumption in kilowatt-hours
        rate: Electricity rate per kWh
        tax_rate: Tax rate as decimal (e.g., 0.08 for 8%)
        
    Returns:
        Total cost including taxes
        
    Raises:
        ValueError: If kwh or rate is negative
        
    Example:
        >>> calculate_energy_cost(100, 0.12, 0.08)
        12.96
    """
    if kwh < 0 or rate < 0:
        raise ValueError("Energy and rate must be non-negative")
    
    base_cost = kwh * rate
    return base_cost * (1 + tax_rate)
```

#### API Documentation

```python
@app.get("/api/devices/{device_ip}/stats")
async def get_device_stats(
    device_ip: str,
    period: str = Query("day", regex="^(hour|day|week|month)$")
) -> dict:
    """
    Get device statistics for specified period.
    
    **Path Parameters:**
    - `device_ip`: IP address of the device
    
    **Query Parameters:**
    - `period`: Time period (hour, day, week, month)
    
    **Returns:**
    ```json
    {
        "device_ip": "192.168.1.100",
        "period": "day",
        "total_kwh": 2.5,
        "average_power": 104.2,
        "peak_power": 1500,
        "cost": 0.30
    }
    ```
    
    **Errors:**
    - 404: Device not found
    - 400: Invalid period
    """
    # Implementation
```

## Pull Request Process

### Before Submitting

1. **Update from upstream:**
```bash
git fetch upstream
git rebase upstream/main
```

2. **Run all tests:**
```bash
./scripts/run-tests.sh
```

3. **Check code style:**
```bash
./scripts/lint.sh
```

4. **Update documentation:**
- Update README if needed
- Add/update API docs
- Update wiki pages

5. **Test your changes:**
```bash
# Build and run locally
docker build -t kasa-monitor:test .
docker run -p 3000:3000 kasa-monitor:test
```

### Creating Pull Request

1. **Push your branch:**
```bash
git push origin feature/your-feature-name
```

2. **Open PR on GitHub:**
- Go to https://github.com/xante8088/kasa-monitor
- Click "Pull requests" → "New pull request"
- Select your branch
- Fill out the PR template

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Tests added/updated
- [ ] All tests passing

## Screenshots (if applicable)
Add screenshots for UI changes

## Related Issues
Fixes #123
```

### Code Review Process

1. **Automated Checks:**
   - CI/CD pipeline runs tests
   - Code coverage verification
   - Linting checks

2. **Review Criteria:**
   - Code quality and style
   - Test coverage
   - Documentation
   - Performance impact
   - Security considerations

3. **Addressing Feedback:**
```bash
# Make requested changes
git add .
git commit -m "fix: address review feedback"
git push origin feature/your-feature-name
```

## Types of Contributions

### Bug Reports

Create an issue with:
- Clear title and description
- Steps to reproduce
- Expected vs actual behavior
- Environment details
- Logs/screenshots

### Feature Requests

Create an issue with:
- Use case description
- Proposed solution
- Alternative solutions
- Implementation ideas

### Security Issues

**DO NOT** create public issues for security vulnerabilities!

Email: security@[project-domain]

Include:
- Description of vulnerability
- Steps to reproduce
- Impact assessment
- Suggested fix if available

### Documentation

- Fix typos and grammar
- Improve clarity
- Add examples
- Update outdated information
- Translate documentation

### Code Contributions

- Bug fixes
- New features
- Performance improvements
- Code refactoring
- Test additions

## Development Guidelines

### Performance

```python
# Use async/await for I/O operations
async def fetch_device_data(device_ip: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://{device_ip}/data") as response:
            return await response.json()

# Batch operations when possible
async def update_multiple_devices(devices: List[str]):
    tasks = [fetch_device_data(ip) for ip in devices]
    return await asyncio.gather(*tasks)
```

### Security

```python
# Validate all inputs
from pydantic import BaseModel, validator, IPvAnyAddress

class DeviceInput(BaseModel):
    device_ip: IPvAnyAddress
    device_name: str
    
    @validator('device_name')
    def validate_name(cls, v):
        if not v or len(v) > 100:
            raise ValueError('Invalid device name')
        return v

# Use parameterized queries
db.execute(
    "SELECT * FROM devices WHERE device_ip = ?",
    (device_ip,)
)  # Good

# Never do this:
db.execute(f"SELECT * FROM devices WHERE device_ip = '{device_ip}'")  # Bad!
```

### Error Handling

```python
# Provide meaningful error messages
class DeviceNotFoundError(Exception):
    def __init__(self, device_ip: str):
        self.device_ip = device_ip
        super().__init__(f"Device not found: {device_ip}")

# Handle errors gracefully
try:
    device = await get_device(device_ip)
except DeviceNotFoundError as e:
    logger.warning(f"Device lookup failed: {e}")
    return JSONResponse(
        status_code=404,
        content={"error": str(e)}
    )
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )
```

## Community

### Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Provide constructive feedback
- Focus on what's best for the community
- Show empathy towards others

### Getting Help

- **Discord**: [Join our server](https://discord.gg/kasamonitor)
- **Discussions**: GitHub Discussions
- **Issues**: GitHub Issues
- **Email**: support@[project-domain]

### Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

## Related Pages

- [Development Setup](Development-Setup) - Detailed setup guide
- [Architecture Overview](Architecture-Overview) - System architecture
- [API Documentation](API-Documentation) - API reference
- [Common Issues](Common-Issues) - Troubleshooting guide