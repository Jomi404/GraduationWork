"""from sqlalchemy import create_engine, Column, Integer, String, JSON, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import json


class PrivacyPolicy(Base):
    __tablename__ = 'privacy_policy'

    id = Column(Integer, primary_key=True)
    content_json = Column(JSON, nullable=False)  # Текст политики в формате JSON
    version = Column(String(10), nullable=False, unique=True)  # Версия, например, "1.0"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # Дата создания
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)  # Дата обновления
    is_active = Column(Boolean, default=True, nullable=False)  # Флаг активности версии


def init_db():
    # Создаем движок для SQLite
    engine = create_engine('sqlite:///privacy_policy.db', echo=True)
    # Создаем таблицу
    Base.metadata.create_all(engine)


def update_policy_section(session, section_key, new_text, new_version):
    # Деактивируем текущую активную версию
    session.query(PrivacyPolicy).filter(PrivacyPolicy.is_active == True).update({"is_active": False})

    # Получаем текущую активную политику
    current_policy = session.query(PrivacyPolicy).filter(PrivacyPolicy.is_active == False).order_by(
        PrivacyPolicy.updated_at.desc()).first()

    # Если есть текущая политика, копируем её JSON и обновляем нужный раздел
    if current_policy:
        content = current_policy.content_json.copy()
    else:
        content = {}

    # Обновляем указанный раздел
    content[section_key] = new_text

    # Создаем новую версию политики
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
    # Инициализация базы данных
    init_db()

    # Пример использования: создание начальной политики и обновление раздела
    engine = create_engine('sqlite:///privacy_policy.db')
    Session = sessionmaker(bind=engine)
    session = Session()

    # Создаем начальную политику
    initial_content = {
        "introduction": "Это введение в политику конфиденциальности.",
        "data_collection": "Мы собираем только необходимые данные.",
        "user_rights": "Пользователи имеют право на удаление данных."
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

    # Обновляем только раздел "data_collection"
    update_policy_section(session, "data_collection", "Мы обновили правила сбора данных.", "2.0")

    # Выводим актуальную политику
    current_policy = session.query(PrivacyPolicy).filter(PrivacyPolicy.is_active == True).first()
    print("Актуальная политика:", json.dumps(current_policy.content_json, indent=2, ensure_ascii=False))"""