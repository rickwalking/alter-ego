"""SQLAlchemy ORM models subpackage. All model classes re-exported here.

Importing the guard modules attaches the run-column atomic-clear listener, the
run-epoch flush fence and the un-archive-on-activity listener (self-registering,
idempotent).
"""

from rag_backend.infrastructure.database.carousel_archive_guard import (
    register_carousel_archive_guard,
)
from rag_backend.infrastructure.database.carousel_run_guard import (
    register_carousel_run_guards,
)
from rag_backend.infrastructure.database.models.autopilot_registry import (
    AUTOPILOT_TABLES as AUTOPILOT_TABLES,
)
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.database.models.carousel import (
    CarouselProjectModel,
    CarouselSlideModel,
    ResearchSourceModel,
)
from rag_backend.infrastructure.database.models.carousel_archive import (
    archivable,
    archive_refusal_of,
    archive_refusals,
    archive_where,
    auto_archivable,
    heartbeat_stale_seconds,
)
from rag_backend.infrastructure.database.models.carousel_artifact_build import (
    CarouselArtifactBuildModel,
)
from rag_backend.infrastructure.database.models.carousel_creator_asset import (
    CarouselCreatorAssetModel,
)
from rag_backend.infrastructure.database.models.carousel_image_generation import (
    CarouselImageGenerationModel,
)
from rag_backend.infrastructure.database.models.content_lock import ContentLockModel
from rag_backend.infrastructure.database.models.conversation import (
    ConversationModel,
    MessageModel,
)
from rag_backend.infrastructure.database.models.document import DocumentModel
from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.infrastructure.database.models.generation_queue_registry import (
    GENERATION_QUEUE_TABLES as GENERATION_QUEUE_TABLES,
)
from rag_backend.infrastructure.database.models.image_bridge_registry import (
    IMAGE_BRIDGE_TABLES as IMAGE_BRIDGE_TABLES,
)
from rag_backend.infrastructure.database.models.notification import NotificationModel
from rag_backend.infrastructure.database.models.palette import PaletteModel
from rag_backend.infrastructure.database.models.persona_correction import (
    PersonaCorrectionModel,
)
from rag_backend.infrastructure.database.models.persona_rubric import (
    PersonaProfileModel,
    QualityRubricModel,
    RubricEvaluationScoreModel,
)
from rag_backend.infrastructure.database.models.source_comment import (
    ContentSourceModel,
    ContentVersionModel,
    EditorialCommentModel,
)
from rag_backend.infrastructure.database.models.user import UserModel
from rag_backend.infrastructure.database.models.workflow_audit_log import (
    WorkflowAuditLogModel,
)

__all__ = [
    "AUTOPILOT_TABLES",
    "GENERATION_QUEUE_TABLES",
    "IMAGE_BRIDGE_TABLES",
    "BlogPostModel",
    "CarouselArtifactBuildModel",
    "CarouselCreatorAssetModel",
    "CarouselImageGenerationModel",
    "CarouselProjectModel",
    "CarouselSlideModel",
    "ContentLockModel",
    "ContentSourceModel",
    "ContentVersionModel",
    "ConversationModel",
    "DocumentModel",
    "EditorialCommentModel",
    "EventOutboxModel",
    "MessageModel",
    "NotificationModel",
    "PaletteModel",
    "PersonaCorrectionModel",
    "PersonaProfileModel",
    "QualityRubricModel",
    "ResearchSourceModel",
    "RubricEvaluationScoreModel",
    "UserModel",
    "WorkflowAuditLogModel",
    "archivable",
    "archive_refusal_of",
    "archive_refusals",
    "archive_where",
    "auto_archivable",
    "heartbeat_stale_seconds",
    "register_carousel_archive_guard",
    "register_carousel_run_guards",
]
