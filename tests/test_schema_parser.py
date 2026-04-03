from pathlib import Path

from dos_machines.application.schema_parser import ConfigSchemaParser


def test_schema_parser_extracts_sections_and_choices() -> None:
    parser = ConfigSchemaParser()
    sample_path = Path("examples/dosbox-staging.conf")
    schema = parser.parse_file(sample_path, engine_id="test-engine", display_name="DOSBox Staging")

    assert schema.sections
    sdl = next(section for section in schema.sections if section.name == "sdl")
    output = next(option for option in sdl.options if option.name == "output")
    fullscreen = next(option for option in sdl.options if option.name == "fullscreen")
    glshader = next(option for section in schema.sections if section.name == "render" for option in section.options if option.name == "glshader")

    assert output.choices[:3] == ["opengl", "texture", "texturenb"]
    assert fullscreen.value_type == "boolean"
    assert glshader.value_type == "dynamic"
    assert "Rendering backend" in output.description
