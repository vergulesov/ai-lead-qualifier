# Architecture

## Overview

AI Lead Qualifier — система квалификации лидов, интегрированная с Bitrix24.

Архитектура разделяет AI-анализ и детерминированную бизнес-логику.

LLM извлекает факты и контекст из сообщений клиента.

Детерминированный pipeline использует накопленное состояние сделки для расчёта квалификации, определения недостающих данных и следующего действия.

## Current pipeline

```text
                    Bitrix24
                       |
             +---------+---------+
             |                   |
             v                   v
         Open Line            Timeline
             |                   |
             +---------+---------+
                       |
                       v
                  Input text
                       |
                       v
                GigaChat Analyzer
                       |
                       v
              Structured AI data
                       |
                       v
          Existing Qualification State
                       |
                       v
                 Field Merger
                       |
                       v
            Cumulative AI Analysis
                       |
             +---------+---------+
             |                   |
             v                   v
          Scoring            Missing Data
             |                   |
             +---------+---------+
                       |
                       v
                Next Step Engine
                       |
                       v
             QualificationResult
                       |
                       v
                  Bitrix24