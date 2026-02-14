"""Token counting and budget management for LLM context."""

import os

import anthropic

from booty.logging import get_logger

logger = get_logger()


class TokenBudget:
    """Manage token budgets and context window limits for LLM calls."""

    def __init__(self, max_context_tokens: int):
        """Initialize token budget manager.

        Args:
            max_context_tokens: Maximum tokens for input context
        """
        self.model = os.environ.get("MAGENTIC_ANTHROPIC_MODEL", "claude-sonnet-4-5")
        self.max_context_tokens = max_context_tokens
        self.max_output_tokens = int(os.environ.get("MAGENTIC_ANTHROPIC_MAX_TOKENS", "4096"))
        self.client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
        logger.info(
            "TokenBudget initialized",
            model=self.model,
            max_context_tokens=max_context_tokens,
            max_output_tokens=self.max_output_tokens,
        )

    def estimate_tokens(self, system_prompt: str, user_content: str) -> int:
        """Estimate token count for given prompts.

        Args:
            system_prompt: System prompt text
            user_content: User message content

        Returns:
            Estimated input token count
        """
        response = self.client.messages.count_tokens(
            model=self.model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        logger.debug(
            "Token count estimated",
            input_tokens=response.input_tokens,
            system_length=len(system_prompt),
            content_length=len(user_content),
        )
        return response.input_tokens

    def check_budget(self, system_prompt: str, user_content: str) -> dict:
        """Check if content fits within token budget.

        Args:
            system_prompt: System prompt text
            user_content: User message content

        Returns:
            Dict with keys:
                - input_tokens: Estimated input token count
                - output_reserved: Tokens reserved for output
                - remaining: Tokens remaining after input + output reservation
                - fits: Whether content fits within budget
                - overflow_by: How many tokens over budget (0 if fits)
        """
        input_tokens = self.estimate_tokens(system_prompt, user_content)
        remaining = self.max_context_tokens - input_tokens - self.max_output_tokens
        fits = remaining >= 0
        overflow_by = max(0, -remaining)

        logger.info(
            "Budget check complete",
            input_tokens=input_tokens,
            output_reserved=self.max_output_tokens,
            remaining=remaining,
            fits=fits,
            overflow_by=overflow_by,
        )

        return {
            "input_tokens": input_tokens,
            "output_reserved": self.max_output_tokens,
            "remaining": remaining,
            "fits": fits,
            "overflow_by": overflow_by,
        }

    def select_files_within_budget(
        self,
        system_prompt: str,
        base_content: str,
        file_contents: dict[str, str],
        max_context: int,
    ) -> dict[str, str]:
        """Select files that fit within token budget.

        Adds files one at a time (sorted by path for determinism) until adding
        the next file would exceed the budget.

        Args:
            system_prompt: System prompt text
            base_content: Base user content (always included)
            file_contents: Dict of file path -> content to consider
            max_context: Maximum context tokens allowed

        Returns:
            Dict of selected file path -> content that fits within budget
        """
        selected = {}
        current_content = base_content

        # Sort files by path for deterministic ordering
        sorted_files = sorted(file_contents.items())

        for filepath, content in sorted_files:
            # Build candidate content with this file added
            candidate_content = current_content + f"\n\n{filepath}:\n{content}"

            # Estimate tokens for candidate
            tokens = self.estimate_tokens(system_prompt, candidate_content)

            # Check if adding this file exceeds budget
            if tokens > max_context:
                logger.warning(
                    "File exceeds budget, stopping selection",
                    filepath=filepath,
                    tokens=tokens,
                    max_context=max_context,
                    files_included=len(selected),
                )
                break

            # File fits, add it
            selected[filepath] = content
            current_content = candidate_content
            logger.debug(
                "File added to budget",
                filepath=filepath,
                tokens=tokens,
                files_included=len(selected),
            )

        # Log summary
        dropped = len(file_contents) - len(selected)
        logger.info(
            "File selection complete",
            files_included=len(selected),
            files_dropped=dropped,
            total_files=len(file_contents),
        )

        return selected
