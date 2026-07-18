# AI Video Dubbing Platform Architecture

## Overview

This document defines the production-grade architecture for an open-source AI Video Dubbing Platform. The architecture is designed to be modular, scalable, GPU-aware, and resilient for large-scale video dubbing workflows.

The platform is defined as a set of independently replaceable engines connected by well-defined interfaces and data contracts.

## Architecture Goals

- Modular engine abstraction for ASR, translation, voice cloning, alignment, and video processing
- Local execution with free open-source components only
- Scalability for videos from 30 seconds to 5+ hours
- Strong observability, checkpointing, and failure recovery
- Production readiness with CI/CD, Docker, and testing strategy
- Maintainable and extensible structure for future model upgrades

## High-Level Architecture

The system is organized into layers:

- `Interface Layer` - engine contracts and domain models
- `Application Layer` - pipeline orchestration and business logic
- `Infrastructure Layer` - concrete engine implementations, storage, model wrappers
- `Integration Layer` - external system adapters: YouTube download, ffmpeg, GPU resources

### Main Engines

1. Speech Recognition Engine
2. Speaker Diarization Engine
3. Alignment Engine
4. Translation Engine
5. Voice Profiling Engine
6. Voice Cloning / Synthesis Engine
7. Lip Sync Engine
8. Video Engine
9. Quality Validation Engine

Each engine exposes a stable interface and a standardized input/output schema. Implementations can be swapped without changing pipeline orchestration.

## Engine Contracts

### Recognition Engine

Responsibility: create timestamped transcripts from audio.

Inputs:
- audio segment path or in-memory waveform
- language hint or source language
- diarization segments (optional)
- ASR config

Outputs:
- transcription segments with text, timestamps, token-level confidence
- language detection metadata
- sentence-level structure

### Diarization Engine

Responsibility: identify speakers and segment audio.

Inputs:
- raw audio path or waveform
- target speaker count preference

Outputs:
- speaker segments with start/end timestamps
- speaker labels and confidence
- segment metadata for downstream mapping

### Alignment Engine

Responsibility: align transcripts to audio at word/phoneme level.

Inputs:
- raw audio
- ASR transcript
- optional speaker segments

Outputs:
- aligned segments with word-level timestamps
- forced alignment corrections for long-form speech
- silence and pause markers

### Translation Engine

Responsibility: produce English target text with natural conversational tone.

Inputs:
- source transcript segments
- source language code
- speaker and scene context
- translation config

Outputs:
- translated segments with segment alignment hints
- translation quality metadata
- alternative phrase suggestions

### Voice Profiling Engine

Responsibility: extract speaker embeddings and prosodic fingerprints.

Inputs:
- speaker audio segments
- raw audio metadata

Outputs:
- speaker embedding vectors
- pitch / energy / rhythm profile
- voice style descriptors (pitch range, speaking rate)

### Voice Cloning Engine

Responsibility: generate speaker-preserving synthesis using translated text.

Inputs:
- target translated text segments
- speaker embedding
- prosody profile
- timing constraints

Outputs:
- synthesized speech audio segments
- duration metadata
- prosody metadata (pitch, energy, pauses)

### Lip Sync Engine

Responsibility: assess and optionally correct visual speech alignment.

Inputs:
- original video frames or segment
- synthesized audio
- alignment metadata

Outputs:
- recommended timings or video render actions
- lip-sync score metadata
- optional corrected video frames

### Video Engine

Responsibility: extract and compose final dubbed video.

Inputs:
- original video
- synthesized audio tracks
- segment metadata
- final encoding config

Outputs:
- final dubbed video file
- intermediate outputs for QA
- composition logs

### Quality Validation Engine

Responsibility: validate output audio/video quality, timing, and translation.

Inputs:
- original and dubbed artifacts
- pipeline metadata

Outputs:
- quality metrics report
- failure or warning signals
- recommended remediation hints

## Component Responsibilities

### `app/`

- Entry point for CLI or service startup
- Configuration initialization
- High-level job submission and orchestration

### `src/core/`

- Pipeline coordinator and workflow manager
- Job state machine and checkpoint management
- Metrics collection and report orchestration

### `src/engines/`

- Engine abstractions and concrete model adapters
- Each engine implementation follows the same interface patterns
- Encapsulates model loading, GPU resource allocation, and inference

### `src/io/`

- External I/O adapters for YouTube download, temp storage, caching
- Checkpoint and manifest storage
- File-system-safe path generation and cleanup

### `src/utils/`

- Shared helpers for audio/video transforms, normalization, logging, and validation
- GPU detection and resource management
- Retry, backoff, and resilience utilities

### `src/models/`

- Domain data schemas
- Pydantic config and runtime validation
- Stable contracts for pipeline stages

### `tests/`

- Unit tests for engine contracts and utilities
- Integration tests for end-to-end pipeline segments
- Benchmark tests for speed, memory, and fidelity

### `docker/` and `ops/`

- Reproducible local environments and container orchestration
- CI workflows, monitoring manifests, and deployment guidelines

## Folder Structure Explained

`app/`
- Contains the executable entry points and bootstrapping logic.
- Minimal logic, delegates to services in `src/`.

`src/`
- Core production code.
- Organizes code by role, not by model.
- Adheres to dependency inversion: higher-level modules depend on interfaces, not implementations.

`src/core/`
- Orchestrates pipeline execution and stage transitions.
- Manages job lifecycle, resume, and error handling.

`src/engines/interfaces/`
- Defines engine contracts using abstract base classes and typed schemas.
- Engine implementations in sibling packages depend on these interfaces.

`src/engines/<engine_name>/`
- Contains model wrappers for each engine.
- Isolated from pipeline logic and from other engines.
- Responsible for loading model artifacts, preprocessing, inference, and postprocessing.

`src/io/`
- Handles downloading, caching, streaming, and persistent state.
- Provides a uniform file storage API for both local disk and future cloud/backing store.

`src/utils/`
- Shared logic that is stateless.
- No dependency on concrete engines.

`src/models/`
- Domain models and validation schemas.
- Should be reused across pipeline and interfaces.

`tests/`
- A well-defined testing structure to validate the product.

`docker/`
- Infrastructure as code for local containerized execution.

`ops/`
- CI/CD configurations and operational guidelines.

`docs/`
- Houses higher-level architecture and planning documents.

## Dependency Direction

- `app/` -> `src/core/`
- `src/core/` -> `src/engines/interfaces/`, `src/io/`, `src/utils/`, `src/models/`
- `src/engines/<impl>/` -> `src/engines/interfaces/`, `src/models/`, `src/utils/`
- `src/io/` -> `src/models/`, `src/utils/`
- `src/utils/` -> standard libraries and third-party libs only
- `tests/` -> everything else

The key rule is that concrete engine implementations must not be imported by the pipeline coordinator directly. The coordinator should instantiate engines through factories or dependency injection.

## Pipeline Data Flow

1. **Download**
   - `YouTubeFetcher` fetches raw video and metadata into a cache.
   - Job manifest is created with source URL, duration, format, and language hints.

2. **Validation**
   - Validate video codec, audio codec, duration, sample rate, and supported formats.
   - Fail fast for unsupported videos.

3. **Audio Extraction**
   - Extract audio track(s) using ffmpeg to standardized WAV/PCM format.
   - Preserve original sample rate and channel metadata.

4. **Noise Reduction & Preprocessing**
   - Optional noise reduction and normalization using librosa or torchaudio.
   - Mark and preserve silence boundaries.

5. **Speaker Detection**
   - Create speaker segments and metadata using pyannote.audio.
   - Assign speaker labels and confidences.

6. **Transcription**
   - ASR engine creates transcripts with timestamps.
   - Segment transcripts by speaker and scene.

7. **Alignment**
   - WhisperX or a forced-aligner refines timestamps at the word/phoneme level.
   - Detect pauses, speech rate, and alignment confidence.

8. **Translation**
   - Translate the source transcript into natural English.
   - Use conversation-aware translation with context preservation.
   - Optionally run a second-stage refinement pass for tone and idiom.

9. **Voice Profiling**
   - Extract speaker embeddings, pitch contours, energy curves, and pause fingerprint.
   - Create a voice style token set for each speaker.

10. **Voice Cloning & Synthesis**
    - Generate synthetic speech for translated text.
    - Condition on speaker embedding and prosody metadata.
    - Use duration control to preserve timing and pauses.

11. **Prosody Transfer & Timing Optimization**
    - Adjust speech rate, pause lengths, and phrase boundaries.
    - Create stretched/compressed audio segments to match original duration.

12. **Lip Sync Optimization**
    - Evaluate audio/video timing with Wav2Lip score.
    - Optionally produce video-compensated output for critical segments.

13. **Audio Mixing**
    - Combine synthesized speech with original background audio.
    - Normalize levels and apply audio mastering heuristics.

14. **Video Merging**
    - Replace original audio with dubbed audio using ffmpeg.
    - Preserve original video quality, subtitles, and timestamps.

15. **Validation & Quality Metrics**
    - Run final QA checks on timing, speaker consistency, and audio artifacts.
    - Generate reports with translation score, voice similarity, and sync metrics.

16. **Cleanup**
    - Remove temporary files based on retention policy.
    - Persist job manifest and quality artifacts for audit.

## Large-Scale Video Support

### Chunking Strategy

- Segment long audio into fixed-size chunks (e.g., 60–120 seconds) during extraction.
- Apply speaker diarization and transcription per chunk with overlap windows for context.
- Keep chunk boundaries aligned to natural speech breaks.

### Streaming and Disk Usage

- Download video in chunks to disk, not memory.
- Use streaming audio extraction and in-place processing to minimize peak memory.
- Store intermediate artifacts in a temporary cache partition with quotas.

### Checkpointing and Resume

- Persist a job manifest with per-chunk status and artifact locations.
- Resume processing from the last successful stage per chunk.
- Support restart after partial failure without reprocessing completed chunks.

### Parallel Workers

- Process independent chunks concurrently when resources allow.
- Use a worker pool or local process manager for CPU-heavy tasks (diarization, translation) and GPU tasks (ASR, TTS).
- Bound parallelism based on GPU memory and CPU cores.

### Fault Isolation

- Treat each chunk as an isolated unit for error recovery.
- Maintain retry logic with backoff for transient failures.
- Persist failures and warnings in job manifests.

### Incremental Outputs

- Write intermediate dubbed audio per chunk.
- Assemble final audio/video after all chunks complete.
- Produce an incremental preview or low-res output for early validation.

## Voice Preservation Architecture

### Voice Cloning Model Evaluation

- Coqui XTTS: strong candidate for local multi-speaker neural TTS with voice cloning support.
- OpenVoice: promising if voice cloning quality and speaker embedding support are production-ready.
- F5-TTS / CosyVoice: useful for specific languages or speed tradeoffs.

### Tradeoffs

- Coqui XTTS: best balance of open-source production readiness, voice cloning support, and integration maturity.
- OpenVoice: may offer more expressive voice cloning but can require more experimentation.
- F5-TTS: fast but may have lower voice similarity and emotional detail.

### Why Coqui XTTS Recommended

- Designed for multi-speaker and speaker embedding workflows.
- Supports prosody conditioning and duration control.
- Actively maintained with open-source ecosystem integration.
- Strong community support for production deployment.

### Voice Preservation Components

- Speaker embeddings derived from audio fingerprints.
- Prosodic profiles capturing pitch, energy, and pause distribution.
- Voice style descriptors to preserve accent and speaking rate.
- TTS conditioning with speaker embedding + prosody metadata.

### Emotion and Prosody

- Preserve emotion by transferring pitch contour and energy dynamics from source to synthesis.
- Preserve speaking speed by aligning synthesized durations to original timestamps.
- Preserve pauses with explicit pause insertion and duration control.

## Translation Architecture

### Model Comparison

- SeamlessM4T: best conversational translation quality and naturalness.
- NLLB-200: robust fallback for broad coverage and multi-language support.
- MarianMT: lightweight option for distilled translation and faster inference.

### Tradeoffs

- SeamlessM4T: stronger natural output, but higher resource consumption.
- NLLB-200: more language coverage, potentially more literal translations.
- MarianMT: smaller models, lower compute, may require tuning for conversational tone.

### Recommendation

- Use SeamlessM4T as the primary translation engine.
- Add NLLB-200 and MarianMT as complementary engines for fallback, quality comparison, and cost-aware execution.
- Implement a refinement pass to convert literal translation into natural English using a small local language model or templated transform.

## Lip Sync Architecture

### Method Evaluation

- Wav2Lip: established open-source solution for audio-driven lip sync.
- MuseTalk: emerging approach with possible visual realism improvements.
- SadTalker: more focused on facial animation than speech-only lip sync.

### Recommendation

- Use Wav2Lip as the first lip-sync evaluation/correction engine.
- Maintain an abstract `LipSyncEngine` interface so future methods such as MuseTalk can be integrated.
- Focus first on audio timing and duration control; use visual correction selectively for critical segments.

## Engineering Standards and Non-Functional Requirements

### Clean Architecture

- Separate use cases from implementation details.
- Keep domain logic independent of frameworks.
- Use interface-driven design and dependency inversion.

### Type Safety and Validation

- Use Python type hints throughout the codebase.
- Use Pydantic for configuration, runtime validation, and parsing external inputs.
- Use dataclasses for simple immutable domain objects.

### Logging and Observability

- Use structured JSON logging.
- Include pipeline trace IDs, chunk IDs, stage names, and engine versions.
- Record warnings and recoverable errors as part of job state.

### Testing Strategy

- Unit tests for engine interfaces, utilities, and config parsing.
- Integration tests for full pipeline stages with synthetic artifacts.
- Benchmark tests for speed, memory, and GPU usage.

### CI/CD

- GitHub Actions for install, lint, type-check, and test pipelines.
- Container validation with Docker build and smoke-run tests.

### Profiling and Benchmarking

- Profile end-to-end pipeline execution for key video lengths.
- Measure ASR, translation, synthesis, and video composition separately.
- Monitor GPU memory usage, CPU utilization, disk I/O, and latency per stage.

### Configuration Management

- Use environment variables and typed config classes.
- Support a `config.yaml` or `.env` override pattern.
- Separate runtime config from job input metadata.

## Failure Modes and Recovery

- Download failure: retry, validate network, fallback to alternate downloader.
- Unsupported formats: fail fast with explicit user guidance.
- ASR errors: retry with alternate model or lower precision.
- Diarization errors: fallback to single-speaker or manual segment boundaries.
- Translation failures: retry with fallback engine, preserve original text if necessary.
- TTS failures: fallback to simpler voice generation or voiceless captions.
- Lip sync mismatch: fallback to duration-only adjustment and warn.

## Quality Metrics

- ASR confidence and transcript coverage
- Translation fluency and sentence completeness
- Speaker embedding similarity vs. source voice
- Prosody and duration match score
- Lip sync score
- Audio level normalization and background preservation
- Job completion success rates and chunk-level errors

## Operational Considerations

- Local-only deployment with optional GPU acceleration
- Resource-aware scheduling and concurrency limits
- Disk quota for temporary artifacts
- Metrics logging for performance and quality improvement
- Extendable to cloud or hybrid deployment in the future

## Final Notes

This architecture is designed to deliver a first-class open-source dubbing platform with enterprise-grade engineering discipline. It emphasizes modularity, production workflows, and robust support for long-form videos.

The next step is to add supporting documents for pipeline contracts, task decomposition, roadmap, and decision records in the repository's `docs/` folder.
