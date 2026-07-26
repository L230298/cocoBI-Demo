"""Tool 2: get_data_source_metadata - 数据源元数据 (PRD §3.3.2)
获取数据集的 Schema(表名、字段、类型、示例、业务术语)
"""
from .registry import register_tool
from services.dataset_registry import get_dataset


@register_tool(
    name="get_data_source_metadata",
    purpose="获取用户上传的数据集 Schema(表名、字段、类型、示例、业务术语)",
    owner_skills=["schema_agent"],
    input_schema={"dataset_id": "string (必填)"},
    output_schema={
        "tables": "list[{name, fields: [{name, type, sample}]}]",
        "business_glossary": "dict[str, str]",
    },
)
def get_data_source_metadata(dataset_id: str) -> dict:
    if not dataset_id:
        return {"success": False, "error_code": "BadRequest", "error_msg": "dataset_id 必填"}

    dataset = get_dataset(dataset_id)
    if not dataset:
        return {
            "success": False,
            "error_code": "NotFound",
            "error_msg": "数据源未找到,请先上传数据",
        }

    return {
        "success": True,
        "tables": [
            {
                "name": dataset["name"],
                "fields": dataset["fields"],
            }
        ],
        "business_glossary": dataset.get("business_glossary", {}),
    }
