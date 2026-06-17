Feature: Conversation SSE chat hook (useSseChat) — AE-0155
  The dashboard conversation chat hook streams assistant replies over SSE,
  reconciles optimistic messages with fetched history, and cleans up correctly
  across the stream lifecycle.

  Scenario: Streaming a reply then finalizing
    Given a conversation id
    When the user sends a message and the stream emits tokens then COMPLETE
    Then the assistant message accumulates the tokens and history is invalidated

  Scenario: Ephemeral (history disabled) chat keeps optimistic messages
    Given enableHistory is false
    When a stream completes
    Then history is not invalidated and the optimistic messages remain

  Scenario: Stream error surfaces an error and stops streaming
    When the stream emits an ERROR event
    Then the hook exposes the error message and isStreaming becomes false

  Scenario: SOURCES event attaches sources to the assistant message
    When the stream emits a SOURCES event after tokens
    Then the assistant message carries the sources

  Scenario: History dedupes optimistic messages by role+content
    Given an optimistic user message
    When the persisted history arrives containing the same role+content
    Then the merged messages contain no duplicate

  Scenario: Guards reject empty content, missing conversation, and concurrent sends
    When the user sends empty content, has no conversation id, or sends while streaming
    Then no new stream is started

  Scenario: finalize is idempotent
    When both the COMPLETE event and onComplete fire
    Then history is invalidated exactly once

  Scenario: startNewChat and unmount abort an in-flight stream
    When the user starts a new chat (or the component unmounts) mid-stream
    Then the in-flight request is aborted and streaming state is reset
