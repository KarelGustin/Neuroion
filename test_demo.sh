#!/bin/bash

echo "🧪 Neuroion Demo Test Script"
echo "============================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}1. Health Check...${NC}"
curl -s http://localhost:8000/health | python3 -m json.tool
echo -e "\n"

echo -e "${BLUE}2. Starting Pairing...${NC}"
PAIR_RESPONSE=$(curl -s -X POST http://localhost:8000/pair/start \
  -H "Content-Type: application/json" \
  -d '{"household_id": 1, "device_id": "demo_001", "device_type": "web", "name": "Demo Device"}')
echo "$PAIR_RESPONSE" | python3 -m json.tool
PAIRING_CODE=$(echo $PAIR_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['pairing_code'])")
echo -e "${GREEN}✓ Pairing code: $PAIRING_CODE${NC}\n"

echo -e "${BLUE}3. Confirming Pairing...${NC}"
CONFIRM_RESPONSE=$(curl -s -X POST http://localhost:8000/pair/confirm \
  -H "Content-Type: application/json" \
  -d "{\"pairing_code\": \"$PAIRING_CODE\", \"device_id\": \"demo_001\"}")
echo "$CONFIRM_RESPONSE" | python3 -m json.tool
TOKEN=$(echo $CONFIRM_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")
echo -e "${GREEN}✓ Token obtained: ${TOKEN:0:30}...${NC}\n"

echo -e "${BLUE}4. Testing Chat (Hello)...${NC}"
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message": "Hello! What can you help me with?"}' | python3 -m json.tool
echo -e "\n"

echo -e "${BLUE}5. Testing Chat (Meal Planning)...${NC}"
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message": "I need help planning meals for this week"}' | python3 -m json.tool
echo -e "\n"

echo -e "${BLUE}6. Submitting Location Event...${NC}"
curl -s -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "event_type": "location",
    "location": {
      "event_type": "arriving_home",
      "timestamp": "2024-01-01T12:00:00",
      "metadata": null
    },
    "health_summary": null
  }' | python3 -m json.tool
echo -e "\n"

echo -e "${GREEN}✅ Demo completed successfully!${NC}"
echo ""
echo "You can also:"
echo "  - View API docs: http://localhost:8000/docs"
echo "  - Test more endpoints interactively"
