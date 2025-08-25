import pytest
import asyncio
import os
import tempfile
import shutil
from unittest.mock import patch
from fastapi import HTTPException

from mockserver.wrappers import call_after_delay, fail_sometimes, random_file_provider


class TestCallAfterDelay:
    """Test cases for the call_after_delay decorator"""

    @pytest.mark.asyncio
    async def test_call_after_delay_decorator(self):
        """Test that the decorator adds delay and preserves function behavior"""
        # Create a simple async function to test
        @call_after_delay(mean=0.01, std_dev=0.005)
        async def test_function():
            return "test_result"

        # Mock asyncio.sleep to avoid actual delays
        with patch('asyncio.sleep') as mock_sleep:
            result = await test_function()
            
            # Verify sleep was called
            mock_sleep.assert_called_once()
            # Verify the function result is preserved
            assert result == "test_result"

    @pytest.mark.asyncio
    async def test_call_after_delay_with_arguments(self):
        """Test that the decorator works with functions that take arguments"""
        @call_after_delay(mean=0.01, std_dev=0.005)
        async def test_function(arg1, arg2, kwarg1=None):
            return f"{arg1}_{arg2}_{kwarg1}"
        
        with patch('asyncio.sleep'):
            result = await test_function("a", "b", kwarg1="c")
            assert result == "a_b_c"


class TestFailSometimes:
    """Test cases for the fail_sometimes decorator"""

    @pytest.mark.asyncio
    async def test_fail_sometimes_never_fails_with_zero_probability(self):
        """Test that function never fails when probability is 0.0"""
        @fail_sometimes(probability=0.0)
        async def test_function():
            return "success"
        
        # Should never fail
        for _ in range(100):
            result = await test_function()
            assert result == "success"

    @pytest.mark.asyncio
    async def test_fail_sometimes_always_fails_with_probability_one(self):
        """Test that function always fails when probability is 1.0"""
        @fail_sometimes(probability=1.0)
        async def test_function():
            return "success"
        
        # Should always fail
        for _ in range(10):
            with pytest.raises(HTTPException) as exc_info:
                await test_function()
            
            assert exc_info.value.status_code == 500
            assert "Mocked failure" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_fail_sometimes_with_arguments(self):
        """Test that the decorator works with functions that take arguments"""
        @fail_sometimes(probability=0.0)  # Never fail for this test
        async def test_function(arg1, arg2, kwarg1=None):
            return f"{arg1}_{arg2}_{kwarg1}"
        
        result = await test_function("a", "b", kwarg1="c")
        assert result == "a_b_c"

    @pytest.mark.asyncio
    async def test_fail_sometimes_error_message_format(self):
        """Test that the error message has the correct format"""
        probability = 0.25
        
        @fail_sometimes(probability=probability)
        async def test_function():
            return "success"
        
        with patch('random.random', return_value=0.1):  # Force failure
            with pytest.raises(HTTPException) as exc_info:
                await test_function()
            
            error_detail = str(exc_info.value.detail)
            assert "Mocked failure" in error_detail
            assert f"Configured to fail {probability:.6f}%" in error_detail


class TestRandomFileProvider:
    """Test cases for the random_file_provider function"""

    def setup_method(self):
        """Set up temporary directory for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_files = ["file1.txt", "file2.txt", "file3.txt"]
        
        # Create test files
        for filename in self.test_files:
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write(f"content for {filename}")

    def teardown_method(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)

    def test_random_file_provider_returns_callable(self):
        """Test that random_file_provider returns a callable function"""
        provider = random_file_provider(self.temp_dir)
        assert callable(provider)
        
    def test_random_file_provider_returns_existing_file(self):
        """Test that the provider returns a path to an existing file"""
        provider = random_file_provider(self.temp_dir)
        
        # Call the provider multiple times to ensure it works
        for _ in range(10):
            filepath = provider()
            assert os.path.exists(filepath)
            assert os.path.isfile(filepath)
            assert os.path.basename(filepath) in self.test_files

    def test_random_file_provider_raises_error_for_nonexistent_directory(self):
        """Test that the provider raises FileNotFoundError for non-existent directory"""
        nonexistent_dir = "/nonexistent/directory"
        
        with pytest.raises(FileNotFoundError) as exc_info:
            random_file_provider(nonexistent_dir)()
        
        assert f"Directory {nonexistent_dir} does not exist" in str(exc_info.value)

    def test_random_file_provider_raises_error_for_empty_directory(self):
        """Test that the provider raises FileNotFoundError for empty directory"""
        empty_dir = tempfile.mkdtemp()
        
        try:
            with pytest.raises(FileNotFoundError) as exc_info:
                random_file_provider(empty_dir)()
            
            assert f"Directory {empty_dir} has no files" in str(exc_info.value)
        finally:
            shutil.rmtree(empty_dir)

    def test_random_file_provider_ignores_subdirectories(self):
        """Test that the provider only considers files, not subdirectories"""
        # Create a subdirectory
        subdir = os.path.join(self.temp_dir, "subdir")
        os.makedirs(subdir)
        
        # Create a file in the subdirectory
        subdir_file = os.path.join(subdir, "subfile.txt")
        with open(subdir_file, 'w') as f:
            f.write("subdirectory content")
        
        provider = random_file_provider(self.temp_dir)
        
        # The provider should only return files from the main directory
        for _ in range(10):
            filepath = provider()
            assert os.path.dirname(filepath) == self.temp_dir
            assert os.path.basename(filepath) in self.test_files

    @patch('random.choice')
    def test_random_file_provider_uses_random_choice(self, mock_choice):
        """Test that the provider uses random.choice to select files"""
        mock_choice.return_value = "file1.txt"
        
        provider = random_file_provider(self.temp_dir)
        result = provider()
        
        # Verify random.choice was called with the list of files
        # Note: os.walk() processes files as it finds them, so we check the call was made
        # but don't assert the exact order of the list
        assert mock_choice.call_count == 1
        called_args = mock_choice.call_args[0][0]
        assert set(called_args) == set(self.test_files)
        assert result == os.path.join(self.temp_dir, "file1.txt")
        
        # Test that a second provider instance works the same way
        mock_choice.reset_mock()
        provider2 = random_file_provider(self.temp_dir)
        result2 = provider2()
        
        assert mock_choice.call_count == 1
        called_args2 = mock_choice.call_args[0][0]
        assert set(called_args2) == set(self.test_files)
        assert result2 == os.path.join(self.temp_dir, "file1.txt")

    def test_random_file_provider_works_without_seed(self):
        """Test that the provider works correctly when no seed is set"""
        # Reset the global seed flag for this test
        import mockserver.wrappers
        original_global_seed = mockserver.wrappers._global_seed
        mockserver.wrappers._global_seed = None
        
        try:
            provider = random_file_provider(self.temp_dir)
            
            # Test multiple calls - should be deterministic due to seed
            results = []
            for _ in range(5):
                result = provider()
                results.append(result)
            
            # With current implementation: seed is set once, then random state advances
            # So results should be different (not identical) as random state progresses
            # But all results should be valid files
            assert len(set(results)) > 1, (
                f"Results should differ as random state advances: {results}"
            )
            for result in results:
                assert os.path.exists(result)
                assert os.path.basename(result) in self.test_files
            
        finally:
            # Restore the original flag state
            mockserver.wrappers._global_seed = original_global_seed

    @patch('os.walk')
    def test_random_file_provider_with_sorted_files(self, mock_walk):
        """Test behavior when file list is sorted (mocked os.walk)"""
        # Reset the global seed flag for this test
        import mockserver.wrappers
        original_global_seed = mockserver.wrappers._global_seed
        mockserver.wrappers._global_seed = None
        
        try:
            # Mock os.walk to return files in a consistent order
            # os.walk returns (root, dirs, files) tuples
            mock_walk.return_value = [(self.temp_dir, [], sorted(self.test_files))]
            
            provider = random_file_provider(self.temp_dir)
            
            # Test multiple times - should be deterministic due to seed
            results = []
            for _ in range(3):
                result = provider()
                results.append(os.path.basename(result))
            
            # With mocked os.walk, the file list is always the same
            # So results may be the same or different depending on random state
            # But all results should be valid files
            for result in results:
                assert result in self.test_files
                
        finally:
            # Restore the original flag state
            mockserver.wrappers._global_seed = original_global_seed


class TestIntegration:
    """Integration tests combining multiple decorators"""

    @pytest.mark.asyncio
    async def test_multiple_decorators_work_together(self):
        """Test that multiple decorators can be applied to the same function"""
        @call_after_delay(mean=0.01, std_dev=0.005)
        @fail_sometimes(probability=0.0)  # Never fail for this test
        async def test_function():
            return "integration_test_result"
        
        with patch('asyncio.sleep'):  # Mock sleep to avoid delays
            result = await test_function()
            assert result == "integration_test_result"

    @pytest.mark.asyncio
    async def test_decorators_preserve_async_behavior(self):
        """Test that decorated functions maintain their async behavior"""
        @call_after_delay(mean=0.01, std_dev=0.005)
        @fail_sometimes(probability=0.0)
        async def test_function():
            await asyncio.sleep(0.001)  # Small async operation
            return "async_result"
        
        with patch('asyncio.sleep') as mock_sleep:
            result = await test_function()
            assert result == "async_result"
            # Should have called sleep twice: once from call_after_delay, once from the function
            assert mock_sleep.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__])
