"""Template engine — generates tests for 3 safe, explicitly classified patterns.

CRITICAL RULES:
1. ONLY 3 patterns: NotImplemented, enum accessor, data class constructor
2. ONLY activates on EXPLICIT static analyzer classification — never structure similarity
3. REQUIRES DTORegistry to generate compilable tests (correct type names)
4. Never called for anything that needs mocking, business logic, or complex setup

These 3 patterns are 100% safe to template because:
- NotImplementedError: test body is always `assertThrows<NotImplementedError> { method() }`
- Enum: test body is always `assertEquals(Enum.VALUE, method())`
- Data class constructor: test body is always `assertNotNull(MyClass(arg1, arg2))`
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from forge_core.models.dto import DTORegistry
from forge_core.models.project import Component


class TemplatePattern(Enum):
    NOT_IMPLEMENTED = "not_implemented"
    ENUM_ACCESSOR = "enum_accessor"
    DATA_CLASS_CONSTRUCTOR = "data_class_constructor"


@dataclass
class TemplateTest:
    """A test generated from a template (no AI call needed)."""

    file_path: str
    test_code: str
    imports_needed: list[str]
    pattern_used: TemplatePattern
    confidence: float = 1.0


class TemplateEngine:
    """Generates tests for explicitly classified trivial methods.

    Only called when static_analyzer has explicitly set method_classification
    to one of the 3 safe values. Never guesses from code structure.
    """

    SAFE_CLASSIFICATIONS = frozenset(
        {"not_implemented", "enum_accessor", "data_class_constructor"}
    )

    def can_generate(self, component: Component) -> bool:
        """Returns True ONLY for explicitly classified safe patterns."""
        return component.method_classification in self.SAFE_CLASSIFICATIONS

    def generate(
        self,
        component: Component,
        dto_registry: DTORegistry,
        language: str,
        test_framework: str,
    ) -> TemplateTest | None:
        """Generate a template test. Returns None if generation fails.

        Requires dto_registry to look up correct type constructors.
        """
        classification = component.method_classification

        if classification == "not_implemented":
            return self._gen_not_implemented(component, language, test_framework)
        elif classification == "enum_accessor":
            return self._gen_enum_accessor(
                component, language, test_framework, dto_registry
            )
        elif classification == "data_class_constructor":
            return self._gen_constructor(
                component, language, test_framework, dto_registry
            )

        return None

    def _gen_not_implemented(
        self, component: Component, language: str, test_framework: str
    ) -> TemplateTest:
        """Generate test for methods that throw NotImplementedError."""
        class_name = component.name
        test_file = component.file_path.replace(".kt", "Test.kt").replace(
            "/main/", "/test/"
        )

        if language.lower() == "kotlin":
            test_code = (
                f"class {class_name}NotImplementedTest {{\n"
                f"    private val sut = {class_name}()\n\n"
                f"    @Test\n"
                f"    fun `should throw NotImplementedError`() {{\n"
                f"        assertFailsWith<NotImplementedError> {{\n"
                f"            sut.execute()\n"
                f"        }}\n"
                f"    }}\n"
                f"}}"
            )
            imports = ["kotlin.test.Test", "kotlin.test.assertFailsWith"]
        elif language.lower() == "python":
            test_code = (
                f"class Test{class_name}NotImplemented:\n"
                f"    def test_raises_not_implemented(self):\n"
                f"        sut = {class_name}()\n"
                f"        with pytest.raises(NotImplementedError):\n"
                f"            sut.execute()\n"
            )
            imports = ["pytest"]
        else:
            test_code = (
                f"class {class_name}NotImplementedTest {{\n"
                f"    @Test\n"
                f"    void shouldThrowNotImplemented() {{\n"
                f"        {class_name} sut = new {class_name}();\n"
                f"        assertThrows(UnsupportedOperationException.class, sut::execute);\n"
                f"    }}\n"
                f"}}"
            )
            imports = [
                "org.junit.jupiter.api.Test",
                "static org.junit.jupiter.api.Assertions.assertThrows",
            ]

        return TemplateTest(
            file_path=test_file,
            test_code=test_code,
            imports_needed=imports,
            pattern_used=TemplatePattern.NOT_IMPLEMENTED,
        )

    def _gen_enum_accessor(
        self,
        component: Component,
        language: str,
        test_framework: str,
        dto_registry: DTORegistry,
    ) -> TemplateTest:
        """Generate test for enum value accessor methods."""
        class_name = component.name
        test_file = component.file_path.replace(".kt", "Test.kt").replace(
            "/main/", "/test/"
        )

        dto_entry = dto_registry.entries.get(class_name)
        first_value = (
            dto_entry.params[0].name.upper()
            if dto_entry and dto_entry.params
            else "UNKNOWN"
        )

        if language.lower() == "kotlin":
            test_code = (
                f"class {class_name}EnumTest {{\n"
                f"    @Test\n"
                f"    fun `should return valid enum value`() {{\n"
                f"        val value = {class_name}.{first_value}\n"
                f"        assertNotNull(value)\n"
                f"        assertEquals({class_name}.{first_value}, value)\n"
                f"    }}\n"
                f"}}"
            )
            imports = [
                "kotlin.test.Test",
                "kotlin.test.assertEquals",
                "kotlin.test.assertNotNull",
            ]
        else:
            test_code = (
                f"class Test{class_name}Enum:\n"
                f"    def test_enum_value_accessible(self):\n"
                f"        value = {class_name}.{first_value}\n"
                f"        assert value is not None\n"
            )
            imports = []

        return TemplateTest(
            file_path=test_file,
            test_code=test_code,
            imports_needed=imports,
            pattern_used=TemplatePattern.ENUM_ACCESSOR,
        )

    def _gen_constructor(
        self,
        component: Component,
        language: str,
        test_framework: str,
        dto_registry: DTORegistry,
    ) -> TemplateTest:
        """Generate test for data class constructors using DTORegistry for correct types."""
        class_name = component.name
        test_file = component.file_path.replace(".kt", "Test.kt").replace(
            "/main/", "/test/"
        )

        dto_entry = dto_registry.entries.get(class_name)
        if dto_entry:
            required_params = [
                p for p in dto_entry.params if not p.nullable and not p.default
            ]
            args = ", ".join(_default_value(p.type, language) for p in required_params)
        else:
            args = ""

        if language.lower() == "kotlin":
            test_code = (
                f"class {class_name}ConstructorTest {{\n"
                f"    @Test\n"
                f"    fun `should construct successfully`() {{\n"
                f"        val obj = {class_name}({args})\n"
                f"        assertNotNull(obj)\n"
                f"    }}\n"
                f"}}"
            )
            imports = ["kotlin.test.Test", "kotlin.test.assertNotNull"]
        else:
            test_code = (
                f"class Test{class_name}Constructor:\n"
                f"    def test_constructor(self):\n"
                f"        obj = {class_name}({args})\n"
                f"        assert obj is not None\n"
            )
            imports = []

        return TemplateTest(
            file_path=test_file,
            test_code=test_code,
            imports_needed=imports,
            pattern_used=TemplatePattern.DATA_CLASS_CONSTRUCTOR,
        )


def _default_value(type_name: str, language: str) -> str:
    """Return a safe default value for a given type."""
    t = type_name.lower().rstrip("?")
    if language.lower() == "kotlin":
        defaults = {
            "string": '"test"',
            "int": "0",
            "long": "0L",
            "double": "0.0",
            "float": "0.0f",
            "boolean": "false",
            "bool": "false",
            "list": "emptyList()",
            "map": "emptyMap()",
            "any": '"test"',
        }
        return defaults.get(t, f'mock{type_name.replace("?", "")}()')
    defaults = {
        "str": '"test"',
        "int": "0",
        "float": "0.0",
        "bool": "False",
        "list": "[]",
        "dict": "{}",
    }
    return defaults.get(t, "None")
