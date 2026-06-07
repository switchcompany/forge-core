"""Tests for forge_core/core/static_analyzer.py — all parsers and classifiers."""
import pytest

from forge_core.core.static_analyzer import (
    FileInfo,
    analyze_statically,
    build_summary_for_ai,
    classify_layer,
    infer_module,
    parse_file,
    _parse_java_kotlin,
    _parse_python,
    _parse_typescript_js,
    _parse_go,
    _parse_csharp,
)


# ── classify_layer ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path,classes,expected", [
    ("src/UserController.kt", ["UserController"], "controller"),
    ("src/routes/auth.ts", [], "controller"),
    ("src/OrderService.kt", ["OrderService"], "service"),
    ("src/use_case/PlaceOrder.py", [], "service"),
    ("src/UserRepository.java", ["UserRepository"], "repository"),
    ("src/models/User.py", ["User"], "model"),
    ("src/config/AppConfig.kt", ["AppConfig"], "config"),
    ("src/utils/StringHelper.py", [], "util"),
    ("src/middleware/AuthMiddleware.ts", [], "middleware"),
    ("src/test/UserTest.java", [], "test"),
    ("src/transformer/OrderMapper.kt", [], "repository"),  # "mapper" matches repository layer
    ("src/something/Random.py", [], "other"),
])
def test_classify_layer(path, classes, expected):
    assert classify_layer(path, classes) == expected


# ── infer_module ──────────────────────────────────────────────────────────────

def test_infer_module_nested_path():
    result = infer_module("src/main/kotlin/orders/OrderService.kt", "src/main/kotlin")
    assert result == "orders"


def test_infer_module_single_level():
    result = infer_module("orders/OrderService.kt", "")
    assert result == "orders"


def test_infer_module_flat_returns_root():
    result = infer_module("MyFile.kt", "src")
    assert result == "root"


# ── _parse_java_kotlin ────────────────────────────────────────────────────────

KOTLIN_SAMPLE = """
package com.example.service

import com.example.repo.UserRepo
import io.ktor.client.HttpClient

@Serializable
data class UserDto(val id: Int, val name: String)

class UserService {
    fun getUser(id: Int): UserDto { return UserDto(id, "test") }
    suspend fun fetchRemote(client: HttpClient): String { return client.get("https://example.com") }
    override fun toString(): String { return "UserService" }
    fun notDone(): String { throw NotImplementedError("not yet") }
    fun alsoNotDone() { TODO() }
}

object Config {
    val apiUrl: String = "https://api.example.com"
}
"""

def test_parse_kotlin_package():
    info = _parse_java_kotlin(KOTLIN_SAMPLE, "src/UserService.kt")
    assert info.package == "com.example.service"


def test_parse_kotlin_imports():
    info = _parse_java_kotlin(KOTLIN_SAMPLE, "src/UserService.kt")
    assert "com.example.repo.UserRepo" in info.imports


def test_parse_kotlin_classes():
    info = _parse_java_kotlin(KOTLIN_SAMPLE, "src/UserService.kt")
    assert "UserService" in info.classes
    assert "Config" in info.classes


def test_parse_kotlin_serializable_dto():
    info = _parse_java_kotlin(KOTLIN_SAMPLE, "src/UserService.kt")
    assert info.has_serializable_dtos
    assert "UserDto" in info.serializable_classes


def test_parse_kotlin_not_implemented_methods():
    info = _parse_java_kotlin(KOTLIN_SAMPLE, "src/UserService.kt")
    assert "notDone" in info.not_implemented_methods or "alsoNotDone" in info.not_implemented_methods


def test_parse_kotlin_line_count():
    info = _parse_java_kotlin(KOTLIN_SAMPLE, "src/UserService.kt")
    assert info.line_count > 5


INLINE_REIFIED_SAMPLE = """
package com.example

object HttpClientWrapper {
    suspend inline fun <reified T> get(url: String, client: HttpClient): T {
        return client.get(url).body()
    }
    suspend inline fun <reified R : Any> post(url: String, client: HttpClient): R {
        return client.post(url).body()
    }
}
"""

def test_parse_kotlin_inline_reified():
    info = _parse_java_kotlin(INLINE_REIFIED_SAMPLE, "src/HttpClientWrapper.kt")
    assert info.has_inline_reified
    assert len(info.inline_reified_methods) >= 1


KOIN_SAMPLE = """
package com.example

class MyService {
    val repo: UserRepo = get<UserRepo>()
    val cache: CacheService = inject<CacheService>()
    val db: Database = get<Database>()
}
"""

def test_parse_kotlin_koin_dependencies():
    info = _parse_java_kotlin(KOIN_SAMPLE, "src/MyService.kt")
    assert "UserRepo" in info.koin_dependencies
    assert "CacheService" in info.koin_dependencies
    assert "Database" in info.koin_dependencies


# ── _parse_python ─────────────────────────────────────────────────────────────

PYTHON_SAMPLE = """
from fastapi import FastAPI, Depends
from app.services import UserService
import os

class UserRouter:
    def __init__(self, service: UserService):
        self.service = service

    async def get_user(self, user_id: int):
        return await self.service.fetch(user_id)

    def health(self):
        return {"status": "ok"}

def create_app() -> FastAPI:
    app = FastAPI()
    return app
"""

def test_parse_python_classes():
    info = _parse_python(PYTHON_SAMPLE, "app/routers/user.py")
    assert "UserRouter" in info.classes


def test_parse_python_methods():
    info = _parse_python(PYTHON_SAMPLE, "app/routers/user.py")
    assert "get_user" in info.methods
    assert "health" in info.methods
    assert "create_app" in info.methods


def test_parse_python_imports():
    info = _parse_python(PYTHON_SAMPLE, "app/routers/user.py")
    assert "fastapi" in info.imports or "FastAPI" in info.imports


def test_parse_python_language_field():
    info = _parse_python(PYTHON_SAMPLE, "app/service.py")
    assert info.language == "python"


def test_parse_python_line_count():
    info = _parse_python(PYTHON_SAMPLE, "app/service.py")
    assert info.line_count > 5


def test_parse_python_private_methods_excluded():
    code = "def _private(): pass\ndef public(): pass\n"
    info = _parse_python(code, "utils.py")
    assert "public" in info.methods
    assert "_private" not in info.methods


# ── _parse_typescript_js ──────────────────────────────────────────────────────

TS_SAMPLE = """
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
const axios = require('axios');

class OrderService {
    constructor(private http: HttpClient) {}
}

export async function placeOrder(data: any): Promise<void> {
    await axios.post('/orders', data);
}

export const getCart = async (userId: string) => {
    return fetch(`/cart/${userId}`);
};
"""

def test_parse_ts_imports():
    info = _parse_typescript_js(TS_SAMPLE, "src/services/order.ts")
    assert "@angular/core" in info.imports or "@angular/common/http" in info.imports


def test_parse_ts_classes():
    info = _parse_typescript_js(TS_SAMPLE, "src/services/order.ts")
    assert "OrderService" in info.classes


def test_parse_ts_functions():
    info = _parse_typescript_js(TS_SAMPLE, "src/services/order.ts")
    assert "placeOrder" in info.methods


def test_parse_ts_arrow_exports():
    info = _parse_typescript_js(TS_SAMPLE, "src/services/order.ts")
    assert "getCart" in info.methods


def test_parse_ts_language_field():
    info = _parse_typescript_js(TS_SAMPLE, "src/order.ts")
    assert info.language == "typescript"


def test_parse_js_language_field():
    info = _parse_typescript_js("const x = 1;", "src/util.js")
    assert info.language == "javascript"


# ── _parse_go ─────────────────────────────────────────────────────────────────

GO_SAMPLE = """
package handlers

import (
    "fmt"
    "net/http"
    "github.com/gin-gonic/gin"
)

type UserHandler struct {
    service UserService
}

func (h *UserHandler) GetUser(c *gin.Context) {
    fmt.Println("get user")
}

func NewUserHandler(s UserService) *UserHandler {
    return &UserHandler{service: s}
}
"""

def test_parse_go_package():
    info = _parse_go(GO_SAMPLE, "handlers/user.go")
    assert info.package == "handlers"


def test_parse_go_structs():
    info = _parse_go(GO_SAMPLE, "handlers/user.go")
    assert "UserHandler" in info.classes


def test_parse_go_functions():
    info = _parse_go(GO_SAMPLE, "handlers/user.go")
    assert "GetUser" in info.methods or "NewUserHandler" in info.methods


def test_parse_go_imports():
    info = _parse_go(GO_SAMPLE, "handlers/user.go")
    assert "net/http" in info.imports or "github.com/gin-gonic/gin" in info.imports


def test_parse_go_language():
    info = _parse_go(GO_SAMPLE, "handlers/user.go")
    assert info.language == "go"


# ── _parse_csharp ─────────────────────────────────────────────────────────────

CS_SAMPLE = """
using System;
using Microsoft.AspNetCore.Mvc;
using MyApp.Services;

namespace MyApp.Controllers {
    public class OrderController : ControllerBase {
        private readonly IOrderService _service;

        public OrderController(IOrderService service) {
            _service = service;
        }

        public async Task<IActionResult> GetOrder(int id) {
            var order = await _service.GetAsync(id);
            return Ok(order);
        }

        private static string BuildUrl(string path) {
            return $"https://api.example.com/{path}";
        }
    }

    public interface IOrderService {}
}
"""

def test_parse_csharp_namespace():
    info = _parse_csharp(CS_SAMPLE, "Controllers/OrderController.cs")
    assert info.package == "MyApp.Controllers"


def test_parse_csharp_classes():
    info = _parse_csharp(CS_SAMPLE, "Controllers/OrderController.cs")
    assert "OrderController" in info.classes
    assert "IOrderService" in info.classes


def test_parse_csharp_methods():
    info = _parse_csharp(CS_SAMPLE, "Controllers/OrderController.cs")
    assert "GetOrder" in info.methods or "BuildUrl" in info.methods


def test_parse_csharp_imports():
    info = _parse_csharp(CS_SAMPLE, "Controllers/OrderController.cs")
    assert "Microsoft.AspNetCore.Mvc" in info.imports


def test_parse_csharp_language():
    info = _parse_csharp(CS_SAMPLE, "Controllers/OrderController.cs")
    assert info.language == "csharp"


# ── parse_file dispatch ───────────────────────────────────────────────────────

@pytest.mark.parametrize("path,expected_lang", [
    ("src/Foo.java", "java"),
    ("src/Foo.kt", "kotlin"),
    ("src/Foo.py", "python"),
    ("src/foo.ts", "typescript"),
    ("src/foo.tsx", "typescript"),
    ("src/foo.js", "javascript"),
    ("src/foo.jsx", "javascript"),
    ("src/foo.go", "go"),
    ("src/Foo.cs", "csharp"),
    ("src/foo.rb", "unknown"),  # generic fallback
])
def test_parse_file_dispatch(path, expected_lang):
    info = parse_file("content", path)
    assert info.language == expected_lang


def test_parse_file_generic_fallback_uses_stem_as_class():
    info = parse_file("some content\nmore content\n", "src/MyLib.rb")
    assert "MyLib" in info.classes


# ── analyze_statically ────────────────────────────────────────────────────────

def test_analyze_statically_returns_file_infos():
    files = {
        "src/service/OrderService.kt": KOTLIN_SAMPLE,
        "app/routes/user.py": PYTHON_SAMPLE,
    }
    results = analyze_statically(files, source_root="src")
    assert len(results) == 2
    paths = {r.path for r in results}
    assert "src/service/OrderService.kt" in paths
    assert "app/routes/user.py" in paths


def test_analyze_statically_sets_layer():
    files = {"src/UserController.kt": "class UserController {}"}
    results = analyze_statically(files)
    assert results[0].layer == "controller"


def test_analyze_statically_sets_module():
    files = {"src/orders/OrderService.kt": "class OrderService {}"}
    results = analyze_statically(files, source_root="src")
    assert results[0].module == "orders"


def test_analyze_statically_empty_returns_empty():
    assert analyze_statically({}) == []


# ── build_summary_for_ai ──────────────────────────────────────────────────────

def test_build_summary_for_ai_contains_file_count():
    files = {
        "src/A.kt": "package a\nclass AService {}",
        "src/B.kt": "package b\nclass BRepo {}",
    }
    infos = analyze_statically(files)
    summary = build_summary_for_ai(infos)
    assert "2 source files" in summary


def test_build_summary_for_ai_shows_testing_signals():
    code = "@Serializable\ndata class Dto(val x: Int)\n"
    infos = analyze_statically({"src/Dto.kt": code})
    summary = build_summary_for_ai(infos)
    assert "@Serializable" in summary or "Serializable" in summary


def test_build_summary_for_ai_empty_infos():
    summary = build_summary_for_ai([])
    assert "0 source files" in summary
