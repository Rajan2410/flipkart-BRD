import enum


class UserRole(str, enum.Enum):
    CENTRAL_ADMIN = "CENTRAL_ADMIN"
    HUB_PICKER = "HUB_PICKER"


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"          # ingested, unclaimed
    IN_PROGRESS = "IN_PROGRESS"  # claimed/locked by a picker
    COMPLETED = "COMPLETED"      # dispatched


class LineStatus(str, enum.Enum):
    PENDING = "PENDING"
    PICKED = "PICKED"    # picked qty reached ordered qty
    SKIPPED = "SKIPPED"  # bypassed by picker


class AuditEvent(str, enum.Enum):
    CLAIM = "CLAIM"
    SCAN = "SCAN"
    INVALID_SCAN = "INVALID_SCAN"
    SKIP = "SKIP"
    COMPLETE = "COMPLETE"
