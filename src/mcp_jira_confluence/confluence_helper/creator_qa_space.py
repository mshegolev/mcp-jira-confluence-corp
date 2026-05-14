from typing import Any, Dict


class CreatorQaSpace:
    @staticmethod
    def generate_space_architecture(
        qa_section_name: str = "QA - Тестирование",
        functional: bool = True,
        integration: bool = True,
        automation: bool = False,
        performance: bool = False,
        test_data: bool = True,
        pdv: bool = False,
        traceability_matrix: bool = True,
        qa_metric: bool = False,
    ) -> Dict[str, Any]:
        main_section_name = qa_section_name
        qa_quality_control = {
            "QA - Контроль качества": [
                {"QA - Функциональное тестирование": functional},
                {"QA - Интеграционное тестирование": integration},
                {"QA - Автоматизированное тестирование": automation},
                {"QA - Нагрузочное тестирование": performance},
                {"QA - Тестовые данные": test_data},
            ]
        }
        qa_quality_assurance = {
            "QA - Обеспечение качества": [
                {"QA - PDV-тесты": pdv},
                {"QA - Monitoring": True},
                {"QA - Автотесты": automation},
            ]
        }
        qa_infrastructure = {"QA - Инфраструктура": [{"QA - Архитектура тестовых стендов": True}]}
        qa_reporting = {
            "QA - Отчетность": [
                {"QA - Матрица покрытия требований": traceability_matrix},
                {"QA - Метрики": qa_metric},
                {"QA - Оценка качества релизов": False},
                {"QA - Отчет о НТ": performance},
                {"QA - Планы": True},
                {"QA - Постмортемы": True},
                {"QA - Шаблон ПМИ": True},
                {"QA - тайминг установки нового релиза в продуктивную среду": True},
            ]
        }
        qa_regulations = {
            "QA - Регламенты": [
                {"QA - Новому сотруднику": True},
                {"QA -SLA": True},
                {"QA - Рабочий процесс группы тестирования": True},
                {"QA - Инструменты группы тестирования": True},
                {"QA - Получение доступов": True},
                {"QA - Роли и ответственность": True},
                {"QA - Стратегия тестирования": True},
                {"QA - TestOps настройка проекта": True},
                {"QA - Верификация workflow/баг менеджмент на проекте": True},
                {"QA - Установка релиза в продуктивную среду": True},
                {"QA - Установка релиза в dev/test/stage/prodlike": True},
                {"QA - Процесс тестирования/верификации": True},
                {"QA - Диагностика запросов": True},
                {"QA - Карта компетенций QA Инженеров": True},
                {"QA - Управление процессом тестирования на проекте": True},
                {"QA - Карта компетенций QA Инженеров": True},
            ]
        }
        qa_contacts: Dict[str, Any] = {"QA - Контакты": {}}
        qa_faq: Dict[str, Any] = {"QA - Вопросы": {}}
        qa_archive: Dict[str, Any] = {"QA - Архив": {}}

        pages = {
            main_section_name: [
                qa_quality_control,
                qa_quality_assurance,
                qa_infrastructure,
                qa_reporting,
                qa_regulations,
                qa_contacts,
                qa_faq,
                qa_archive,
            ]
        }
        return pages
