"""Template-independent generation orchestration."""

from forgepy.config import ProjectConfig
from forgepy.models import ProjectSpec, TemplateRegistry
from forgepy.utils.filesystem import write_project


def build_spec(config: ProjectConfig, registry: TemplateRegistry) -> ProjectSpec:
    return registry.get(config.template_id).builder(config)


def generate(config: ProjectConfig, registry: TemplateRegistry) -> ProjectSpec:
    spec = build_spec(config, registry)
    write_project(config.destination, spec)
    return spec
