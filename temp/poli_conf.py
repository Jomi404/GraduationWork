"""from sqlalchemy import create_engine, Column, Integer, String, JSON, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import json


class PrivacyPolicy(Base):
    __tablename__ = 'privacy_policy'

    id = Column(Integer, primary_key=True)
    content_json = Column(JSON, nullable=False)  # ����� �������� � ������� JSON
    version = Column(String(10), nullable=False, unique=True)  # ������, ��������, "1.0"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # ���� ��������
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)  # ���� ����������
    is_active = Column(Boolean, default=True, nullable=False)  # ���� ���������� ������


def init_db():
    # ������� ������ ��� SQLite
    engine = create_engine('sqlite:///privacy_policy.db', echo=True)
    # ������� �������
    Base.metadata.create_all(engine)


def update_policy_section(session, section_key, new_text, new_version):
    # ������������ ������� �������� ������
    session.query(PrivacyPolicy).filter(PrivacyPolicy.is_active == True).update({"is_active": False})

    # �������� ������� �������� ��������
    current_policy = session.query(PrivacyPolicy).filter(PrivacyPolicy.is_active == False).order_by(
        PrivacyPolicy.updated_at.desc()).first()

    # ���� ���� ������� ��������, �������� � JSON � ��������� ������ ������
    if current_policy:
        content = current_policy.content_json.copy()
    else:
        content = {}

    # ��������� ��������� ������
    content[section_key] = new_text

    # ������� ����� ������ ��������
    new_policy = PrivacyPolicy(
        content_json=content,
        version=new_version,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_active=True
    )
    session.add(new_policy)
    session.commit()


if __name__ == "__main__":
    # ������������� ���� ������
    init_db()

    # ������ �������������: �������� ��������� �������� � ���������� �������
    engine = create_engine('sqlite:///privacy_policy.db')
    Session = sessionmaker(bind=engine)
    session = Session()

    # ������� ��������� ��������
    initial_content = {
        "introduction": "��� �������� � �������� ������������������.",
        "data_collection": "�� �������� ������ ����������� ������.",
        "user_rights": "������������ ����� ����� �� �������� ������."
    }
    initial_policy = PrivacyPolicy(
        content_json=initial_content,
        version="1.0",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_active=True
    )
    session.add(initial_policy)
    session.commit()

    # ��������� ������ ������ "data_collection"
    update_policy_section(session, "data_collection", "�� �������� ������� ����� ������.", "2.0")

    # ������� ���������� ��������
    current_policy = session.query(PrivacyPolicy).filter(PrivacyPolicy.is_active == True).first()
    print("���������� ��������:", json.dumps(current_policy.content_json, indent=2, ensure_ascii=False))"""