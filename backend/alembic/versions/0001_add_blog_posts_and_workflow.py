"""Add blog posts, content versions, editorial comments, persona profiles, and workflow extensions.

Revision ID: 0001_add_blog_posts_and_workflow
Revises: 
Create Date: 2026-05-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers
revision = '0001_add_blog_posts_and_workflow'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create blog_posts table
    op.create_table(
        'blog_posts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), unique=True, nullable=False),
        sa.Column('status', sa.String(50), default='draft', nullable=False),
        sa.Column('content', postgresql.JSONB, default=dict, nullable=False),
        sa.Column('excerpt', sa.String(500), nullable=True),
        sa.Column('featured_image_url', sa.String(500), nullable=True),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('editor_comments', postgresql.JSON, default=list, nullable=False),
        sa.Column('version_history', postgresql.JSON, default=list, nullable=False),
        sa.Column('sources', postgresql.JSON, default=list, nullable=False),
        sa.Column('citations', postgresql.JSON, default=list, nullable=False),
        sa.Column('ai_suggestions', postgresql.JSON, default=list, nullable=False),
        sa.Column('ai_generation_metadata', postgresql.JSON, default=dict, nullable=False),
        sa.Column('meta_title', sa.String(255), nullable=True),
        sa.Column('meta_description', sa.String(500), nullable=True),
        sa.Column('keywords', postgresql.JSON, default=list, nullable=False),
        sa.Column('canonical_url', sa.String(500), nullable=True),
        sa.Column('view_count', sa.Integer, default=0, nullable=False),
        sa.Column('like_count', sa.Integer, default=0, nullable=False),
        sa.Column('comment_count', sa.Integer, default=0, nullable=False),
        sa.Column('share_count', sa.Integer, default=0, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('submitted_for_review_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scheduled_publish_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create content_versions table
    op.create_table(
        'content_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('content_id', sa.String(36), nullable=False),
        sa.Column('content_type', sa.String(30), nullable=False),
        sa.Column('version_number', sa.Integer, nullable=False),
        sa.Column('snapshot', postgresql.JSON, nullable=False),
        sa.Column('change_summary', sa.String(500), nullable=True),
        sa.Column('author_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Create editorial_comments table
    op.create_table(
        'editorial_comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('content_id', sa.String(36), nullable=False),
        sa.Column('content_type', sa.String(50), nullable=False),
        sa.Column('author_id', sa.String(36), nullable=False),
        sa.Column('text', sa.Text, nullable=False),
        sa.Column('position', postgresql.JSON, nullable=True),
        sa.Column('status', sa.String(20), default='open', nullable=False),
        sa.Column('ai_suggestion', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create persona_profiles table
    op.create_table(
        'persona_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tone_attributes', postgresql.JSON, default=lambda: {"formal": 0.3, "conversational": 0.8, "humorous": 0.4}, nullable=False),
        sa.Column('writing_samples', postgresql.JSON, default=list, nullable=False),
        sa.Column('forbidden_phrases', postgresql.JSON, default=list, nullable=False),
        sa.Column('preferred_phrases', postgresql.JSON, default=list, nullable=False),
        sa.Column('sentence_structure_preferences', sa.Text, nullable=True),
        sa.Column('paragraph_style', sa.Text, nullable=True),
        sa.Column('opinion_expression', sa.Text, nullable=True),
        sa.Column('expertise_areas', postgresql.JSON, default=list, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('version', sa.Integer, default=1, nullable=False),
    )
    
    # Create quality_rubrics table
    op.create_table(
        'quality_rubrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('criteria', postgresql.JSON, default=list, nullable=False),
        sa.Column('applicable_content_types', postgresql.JSON, default=list, nullable=False),
        sa.Column('is_default', sa.Boolean, default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('version', sa.Integer, default=1, nullable=False),
    )
    
    # Create content_sources table
    op.create_table(
        'content_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=True),
        sa.Column('blog_post_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('blog_posts.id', ondelete='CASCADE'), nullable=True),
        sa.Column('source_type', sa.String(20), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('content_metadata', postgresql.JSON, default=dict, nullable=False),
        sa.Column('tags', postgresql.JSON, default=list, nullable=False),
        sa.Column('extracted_key_points', postgresql.JSON, default=list, nullable=False),
        sa.Column('is_primary', sa.Boolean, default=False, nullable=False),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Create rubric_evaluation_scores table
    op.create_table(
        'rubric_evaluation_scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('rubric_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('quality_rubrics.id'), nullable=False),
        sa.Column('content_id', sa.String(36), nullable=False),
        sa.Column('content_type', sa.String(30), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('scores', postgresql.JSON, default=dict, nullable=False),
        sa.Column('overall_score', sa.Integer, default=0, nullable=False),
        sa.Column('passed', sa.Boolean, default=False, nullable=False),
        sa.Column('feedback', postgresql.JSON, default=list, nullable=False),
    )
    
    # Add workflow extension columns to projects table
    op.add_column('projects', sa.Column('creative_brief', sa.Text, nullable=True))
    op.add_column('projects', sa.Column('persona_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('projects', sa.Column('rubric_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('projects', sa.Column('instructions', sa.Text, nullable=True))
    op.add_column('projects', sa.Column('current_phase', sa.String(50), sa.Default('brief'), nullable=False))
    op.add_column('projects', sa.Column('phase_status', sa.String(50), sa.Default('pending'), nullable=False))
    
    # Create indexes
    op.create_index('ix_blog_posts_status', 'blog_posts', ['status'])
    op.create_index('ix_blog_posts_slug', 'blog_posts', ['slug'])
    op.create_index('ix_blog_posts_author', 'blog_posts', ['author_id'])
    op.create_index('ix_blog_posts_project', 'blog_posts', ['project_id'])
    op.create_index('ix_content_versions_content_id', 'content_versions', ['content_id'])
    op.create_index('ix_content_versions_type', 'content_versions', ['content_type'])
    op.create_index('ix_content_versions_version', 'content_versions', ['content_type', 'version_number'], unique=True)
    op.create_index('ix_editorial_comments_content_id', 'editorial_comments', ['content_id'])
    op.create_index('ix_editorial_comments_status', 'editorial_comments', ['status'])
    op.create_index('ix_persona_profiles_name', 'persona_profiles', ['name'])
    op.create_index('ix_persona_profiles_version', 'persona_profiles', ['version'])
    op.create_index('ix_quality_rubrics_name', 'quality_rubrics', ['name'])
    op.create_index('ix_quality_rubrics_is_default', 'quality_rubrics', ['is_default'])
    op.create_index('ix_content_sources_project_id', 'content_sources', ['project_id'])
    op.create_index('ix_content_sources_blog_post_id', 'content_sources', ['blog_post_id'])
    op.create_index('ix_content_sources_type', 'content_sources', ['source_type'])
    op.create_index('ix_rubric_scores_rubric_id', 'rubric_evaluation_scores', ['rubric_id'])
    op.create_index('ix_rubric_scores_content_id', 'rubric_evaluation_scores', ['content_id'])
    op.create_index('ix_rubric_scores_content_type', 'rubric_evaluation_scores', ['content_type'])
    op.create_index('ix_projects_phase', 'projects', ['current_phase', 'phase_status'])
    
    # Create foreign key constraints
    op.create_foreign_key(
        'fk_content_sources_project',
        'content_sources',
        'projects',
        ['project_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_content_sources_blog_post',
        'content_sources',
        'blog_posts',
        ['blog_post_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_editorial_comments_content',
        'editorial_comments',
        'blog_posts',
        ['content_id'],
        ['id']
    )
    op.create_foreign_key(
        'fk_content_versions_content',
        'content_versions',
        'blog_posts',
        ['content_id'],
        ['id']
    )
    op.create_foreign_key(
        'fk_rubric_scores_rubric',
        'rubric_evaluation_scores',
        'quality_rubrics',
        ['rubric_id'],
        ['id']
    )


def downgrade():
    # Drop foreign key constraints
    op.drop_constraint('fk_rubric_scores_rubric', 'rubric_evaluation_scores', type_='foreignkey')
    op.drop_constraint('fk_content_versions_content', 'content_versions', type_='foreignkey')
    op.drop_constraint('fk_editorial_comments_content', 'editorial_comments', type_='foreignkey')
    op.drop_constraint('fk_content_sources_blog_post', 'content_sources', type_='foreignkey')
    op.drop_constraint('fk_content_sources_project', 'content_sources', type_='foreignkey')
    
    # Drop indexes
    op.drop_index('ix_projects_phase', table_name='projects')
    op.drop_index('ix_rubric_scores_content_type', table_name='rubric_evaluation_scores')
    op.drop_index('ix_rubric_scores_content_id', table_name='rubric_evaluation_scores')
    op.drop_index('ix_rubric_scores_rubric_id', table_name='rubric_evaluation_scores')
    op.drop_index('ix_content_sources_type', table_name='content_sources')
    op.drop_index('ix_content_sources_blog_post_id', table_name='content_sources')
    op.drop_index('ix_content_sources_project_id', table_name='content_sources')
    op.drop_index('ix_quality_rubrics_is_default', table_name='quality_rubrics')
    op.drop_index('ix_quality_rubrics_name', table_name='quality_rubrics')
    op.drop_index('ix_persona_profiles_version', table_name='persona_profiles')
    op.drop_index('ix_persona_profiles_name', table_name='persona_profiles')
    op.drop_index('ix_editorial_comments_status', table_name='editorial_comments')
    op.drop_index('ix_editorial_comments_content_id', table_name='editorial_comments')
    op.drop_index('ix_content_versions_version', table_name='content_versions')
    op.drop_index('ix_content_versions_type', table_name='content_versions')
    op.drop_index('ix_content_versions_content_id', table_name='content_versions')
    op.drop_index('ix_blog_posts_project', table_name='blog_posts')
    op.drop_index('ix_blog_posts_author', table_name='blog_posts')
    op.drop_index('ix_blog_posts_slug', table_name='blog_posts')
    op.drop_index('ix_blog_posts_status', table_name='blog_posts')
    
    # Drop columns from projects table
    op.drop_column('projects', 'phase_status')
    op.drop_column('projects', 'current_phase')
    op.drop_column('projects', 'instructions')
    op.drop_column('projects', 'rubric_id')
    op.drop_column('projects', 'persona_id')
    op.drop_column('projects', 'creative_brief')
    
    # Drop tables
    op.drop_table('rubric_evaluation_scores')
    op.drop_table('content_sources')
    op.drop_table('quality_rubrics')
    op.drop_table('persona_profiles')
    op.drop_table('editorial_comments')
    op.drop_table('content_versions')
    op.drop_table('blog_posts')
