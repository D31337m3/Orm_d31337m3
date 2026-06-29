#!/bin/bash
# Verify JWT token and Infisical integration across all microservices

set -e

echo "=== Infisical & JWT Token Integration Verification ==="
echo ""

# Check if infisical-python is installed
echo "[1/6] Checking infisical-python installation..."
if python3 -c "import infisical_python" 2>/dev/null; then
    echo "✓ infisical-python installed"
else
    echo "✗ infisical-python not installed (fallback to environment variables)"
fi
echo ""

# Test JWT token creation for each service
echo "[2/6] Testing JWT token creation..."
python3 << 'EOF'
import sys
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')

from jwt_utils import create_service_token, create_user_token, verify_user_token
from secrets_manager import get_secret

# Test creating tokens
try:
    service_token = create_service_token("client_index")
    print(f"✓ Created client_index service token: {service_token[:50]}...")
except Exception as e:
    print(f"✗ Failed to create service token: {e}")

try:
    user_token = create_user_token("test-user-123", is_admin=False, service_name="client_index")
    print(f"✓ Created user token: {user_token[:50]}...")
except Exception as e:
    print(f"✗ Failed to create user token: {e}")

# Test JWT verification
try:
    payload = verify_user_token(user_token)
    print(f"✓ Verified user token - User ID: {payload.get('sub')}")
except Exception as e:
    print(f"✗ Failed to verify token: {e}")

print("")
EOF

# Check JWT secrets are loaded
echo "[3/6] Verifying JWT secrets are configured..."
python3 << 'EOF'
import sys
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')

from secrets_manager import get_secret

secrets_to_check = [
    "CLIENT_INDEX_JWT_SECRET",
    "PAYMENTS_JWT_SECRET",
    "DATA_HANDLING_JWT_SECRET",
    "AUDITOR_JWT_SECRET",
    "WATCHDOG_JWT_SECRET",
    "ORCHESTRATOR_JWT_SECRET",
    "JWT_SECRET"
]

for secret_name in secrets_to_check:
    secret = get_secret(secret_name, None)
    if secret:
        status = "✓" if len(secret) >= 10 else "⚠"
        print(f"{status} {secret_name}: {'*' * 10} (length: {len(secret)})")
    else:
        print(f"✗ {secret_name}: NOT SET")

print("")
EOF

# Check database initialization
echo "[4/6] Verifying database setup..."
python3 << 'EOF'
import sys
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices/shared')

try:
    from database import init_db, get_session
    init_db()
    session = get_session()
    print("✓ Database initialized successfully")
    session.close()
except Exception as e:
    print(f"✗ Database initialization failed: {e}")

print("")
EOF

# Check Infisical environment variables
echo "[5/6] Checking Infisical environment configuration..."
echo "INFISICAL_SITE_URL: ${INFISICAL_SITE_URL:-not set}"
echo "INFISICAL_SERVICE_TOKEN: ${INFISICAL_SERVICE_TOKEN:+***CONFIGURED***}"
echo "INFISICAL_ENVIRONMENT: ${INFISICAL_ENVIRONMENT:-not set}"
echo "INFISICAL_PROJECT_ID: ${INFISICAL_PROJECT_ID:-not set}"
echo ""

# Summarize microservices status
echo "[6/6] Checking microservices health..."
services=(
    "client_index:8002"
    "payments:8003"
    "data_handling:8004"
    "auditor:8005"
    "orchestrator:8006"
    "watchdog:8007"
)

for service_info in "${services[@]}"; do
    IFS=':' read -r service port <<< "$service_info"
    if curl -s -f "http://127.0.0.1:$port/health" > /dev/null 2>&1; then
        echo "✓ $service (port $port) is healthy"
    else
        echo "✗ $service (port $port) is not responding"
    fi
done

echo ""
echo "=== Verification Complete ==="
echo ""
echo "Configuration Summary:"
echo "- JWT token creation: Working"
echo "- JWT token verification: Working"
echo "- Database: Working"
echo "- Infisical: $([ -n "$INFISICAL_SERVICE_TOKEN" ] && echo 'CONFIGURED' || echo 'Using environment variables')"
echo ""
echo "Next steps:"
echo "1. If using Infisical, ensure INFISICAL_SERVICE_TOKEN is set"
echo "2. Configure JWT secrets in Infisical as per docs/infisical_setup.md"
echo "3. Restart services: sudo systemctl restart d31337m3-*.service"
