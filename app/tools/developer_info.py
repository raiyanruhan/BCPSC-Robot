import os
from app.schemas import GetDeveloperInfoArgs
import logging

logger = logging.getLogger(__name__)

# Load developer names from dev.md
DEVELOPER_NAMES = []

def _load_developer_names():
    """Load developer names from dev.md file."""
    global DEVELOPER_NAMES
    
    if DEVELOPER_NAMES:
        return  # Already loaded
    
    dev_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "Data", "Developers", "dev.md")
    if os.path.exists(dev_file_path):
        try:
            with open(dev_file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and section headers
                    if line and not line.startswith("Extras:") and not line.startswith("#"):
                        DEVELOPER_NAMES.append(line)
            logger.info(f"Loaded {len(DEVELOPER_NAMES)} developer names")
        except Exception as e:
            logger.error(f"Error loading developer names: {e}")
            DEVELOPER_NAMES = []
    else:
        logger.warning(f"Developer file not found at {dev_file_path}")

def _normalize_name(name: str) -> str:
    """Normalize name for better matching (remove spaces, convert to lowercase, handle variations)."""
    normalized = name.lower().replace(" ", "").replace("-", "").replace("_", "")
    return normalized

def _fuzzy_match(query: str, dev_name: str) -> bool:
    """Check if query matches developer name with fuzzy matching."""
    query_norm = _normalize_name(query)
    dev_norm = _normalize_name(dev_name)
    
    # Exact match
    if query_norm == dev_norm:
        return True
    
    # Check if query is contained in dev name or vice versa
    if query_norm in dev_norm or dev_norm in query_norm:
        return True
    
    # Check if first few characters match (for nicknames like "faizuz" -> "faijuice")
    if len(query_norm) >= 4 and query_norm[:4] in dev_norm:
        return True
    if len(dev_norm) >= 4 and dev_norm[:4] in query_norm:
        return True
    
    # Check individual words
    query_words = query.lower().split()
    dev_words = dev_name.lower().split()
    for qw in query_words:
        for dw in dev_words:
            if qw in dw or dw in qw:
                if len(qw) >= 3 or len(dw) >= 3:  # Only match if word is at least 3 chars
                    return True
    
    return False

async def get_developer_info(args: GetDeveloperInfoArgs) -> dict:
    """
    Returns info for a developer from the local developer list.
    """
    _load_developer_names()
    
    query = args.developer_name
    query_lower = query.lower()
    
    # Check if query is asking about the robot/team itself
    if any(term in query_lower for term in ["who developed", "who created", "who built", "who made", "developer", "development team", "robot brain"]):
        return {
            "developer_name": "Robot Brain Development Team",
            "team_name": "Robot Brain Development Team",
            "is_team_member": True,
            "team_members": DEVELOPER_NAMES,
            "lead_developer": "Raiyan & Jotirmoy & Farsad",
            "organization": "Robot Brain Project",
            "about": "We developed this robot using Gemini AI + robotics tools. The team consists of talented developers working on the humanoid robot project.",
            "contact": "Part of the Robot Brain project team",
            "note": "This is the development team behind the Robot Brain humanoid robot project."
        }
    
    # Check if developer name matches (case-insensitive partial match with fuzzy matching)
    matched_developers = []
    for dev_name in DEVELOPER_NAMES:
        if _fuzzy_match(query, dev_name):
            matched_developers.append(dev_name)
    
    if matched_developers:
        # Return the first match or exact match if available
        exact_match = next((d for d in matched_developers if d.lower() == query_lower), None)
        developer_name = exact_match or matched_developers[0]
        
        return {
            "developer_name": developer_name,
            "is_team_member": True,
            "team": "Robot Brain Development Team",
            "team_members": DEVELOPER_NAMES,
            "organization": "Robot Brain Project",
            "note": f"{developer_name} is part of the Robot Brain development team."
        }
    
    return {
        "developer_name": query,
        "is_team_member": False,
        "team": "Robot Brain Development Team",
        "team_members": DEVELOPER_NAMES,
        "error": "Developer not found in the team database",
        "note": f"'{query}' is not found in our development team database. The team consists of: {', '.join(DEVELOPER_NAMES[:5])}{' and more' if len(DEVELOPER_NAMES) > 5 else ''}."
    }

definition = {
    "name": "getDeveloperInfo",
    "description": "CRITICAL: Use this tool FIRST when users ask about developers, team members, or who created/built the robot. This tool checks the Robot Brain development team database. ALWAYS use this before searchPerson when the query might be about a developer. Use this for: 'Who developed you?', 'Who created this robot?', 'Who is [name]?' (if name might be a developer), questions about team members, or any developer-related queries. Returns team information, member list, and organization details. If the person is not found in the developer database, then you can use searchPerson as a fallback.",
    "parameters": {
        "type": "object",
        "properties": {
            "developer_name": {"type": "string", "description": "Name of the developer to check (can be full name, nickname, or partial name), or questions like 'who developed you', 'who created this', 'development team', etc."}
        },
        "required": ["developer_name"]
    }
}
