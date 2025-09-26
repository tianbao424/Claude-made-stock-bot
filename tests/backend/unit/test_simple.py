"""
简单测试示例 - 验证测试框架工作
"""
import pytest


def test_simple_assertion():
    """简单的断言测试"""
    assert 1 + 1 == 2


def test_string_operations():
    """字符串操作测试"""
    text = "AI股票助手"
    assert len(text) == 6
    assert "股票" in text


class TestMathOperations:
    """数学运算测试类"""
    
    def test_addition(self):
        """加法测试"""
        assert 5 + 3 == 8
    
    def test_multiplication(self):
        """乘法测试"""
        assert 4 * 6 == 24
    
    def test_division(self):
        """除法测试"""
        assert 10 / 2 == 5.0


@pytest.mark.asyncio
async def test_async_function():
    """异步函数测试"""
    import asyncio
    
    async def async_add(a, b):
        await asyncio.sleep(0.01)  # 模拟异步操作
        return a + b
    
    result = await async_add(3, 4)
    assert result == 7


def test_list_operations():
    """列表操作测试"""
    test_list = [1, 2, 3, 4, 5]
    
    assert len(test_list) == 5
    assert 3 in test_list
    assert max(test_list) == 5
    assert min(test_list) == 1


def test_dictionary_operations():
    """字典操作测试"""
    test_dict = {
        "stock_code": "000001",
        "stock_name": "平安银行", 
        "price": 13.20
    }
    
    assert test_dict["stock_code"] == "000001"
    assert "stock_name" in test_dict
    assert test_dict.get("price") == 13.20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])