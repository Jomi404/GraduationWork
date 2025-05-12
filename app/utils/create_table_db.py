from sqlalchemy import create_engine, Column, Integer, String, JSON, Boolean, DateTime, BigInteger
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from environs import Env

env = Env()
env.read_env()

Base = declarative_base()


class Admin(Base):
    """A model for storing admin information.
    Fields:
        id: int - The unique identifier of the record.
        tg_id: bigint - Telegram user ID associated with the admin.
        name: str - The name of the admin.
        created_at: datetime - Time when the admin record was created.
    """
    __tablename__ = 'admin'

    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PrivacyPolicy(Base):
    """A model for storing a privacy policy.
    Fields:
        id: int is the unique identifier of the record.
        content_json: jsonb - Policy sections in the format {"introduction": "Text", ...}.
        version: str - Policy version (for example, "1.0").
        created_at: datetime - Policy creation time.
        updated_at: datetime - Time of the last policy update.
        is_active: boolean - Flag indicating the active version of the policy.
    """
    __tablename__ = 'privacy_policy'

    id = Column(Integer, primary_key=True)
    content_json = Column(JSON, nullable=False)
    version = Column(String(10), nullable=False, unique=True)  # Version, e.g., "1.0"
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


def init_db():
    """Creates a privacy_policy table in the PostgreSQL database."""

    db_user = env.str("DB_USER")
    db_password = env.str('DB_PASSWORD')
    db_host = env.str('DB_HOST')
    db_port = env.str('DB_PORT')
    db_name = env.str('DB_NAME')

    connection_string = (
        f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )

    engine = create_engine(connection_string, echo=True)

    # Create table
    Base.metadata.create_all(engine)
    return engine


def update_policy_section(session, section_key, new_text, new_version):
    """Updates the specified policy section by creating a new version."""

    # Deactivate current active version
    session.query(PrivacyPolicy).filter(PrivacyPolicy.is_active).update({"is_active": False})

    # Get the latest (now deactivated) version
    current_policy = session.query(PrivacyPolicy).filter(~PrivacyPolicy.is_active).order_by(
        PrivacyPolicy.updated_at.desc()).first()

    # Copy existing JSON content or create new
    content = current_policy.content_json.copy() if current_policy else {}

    # Update specified section
    content[section_key] = new_text

    # Create new policy version
    new_policy = PrivacyPolicy(
        content_json=content,
        version=new_version,
        is_active=True
    )
    session.add(new_policy)
    session.commit()
