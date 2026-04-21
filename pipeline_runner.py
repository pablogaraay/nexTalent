from __future__ import annotations
import os
import time
import traceback
from datetime import datetime, timezone

INTERVAL_HOURS = int(os.getenv("PIPELINE_INTERVAL_HOURS", "12"))
INTERVAL_SECONDS = INTERVAL_HOURS * 3600


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _separator(label: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"  {_now()}")
    print(f"{'=' * 60}\n")


def run_llm_processing() -> bool:
    _separator("PASO 3 — Extracción LLM (llm_processor)")
    try:
        from llm_processor import LLMProcessor
        from config import Config

        processor = LLMProcessor()
        processor.process_all_batches(batch_size=Config.BATCH_SIZE)
        print("✓ LLM processing completado correctamente.")
        return True
    except SystemExit:
        print("⚠ Cuota de Groq agotada (exit detectado).")
        print("  → Se continuará con index_taxonomy + map_offers")
        print("    para mapear las ofertas ya procesadas.")
        return False
    except Exception as exc:
        print(f"✗ Error inesperado en LLM processing: {exc}")
        traceback.print_exc()
        return False


def run_index_taxonomy() -> bool:
    _separator("PASO 4 — Indexar taxonomías (index_taxonomy)")
    try:
        from rag.index_taxonomy import main as index_main
        index_main()
        print("✓ Taxonomías indexadas correctamente.")
        return True
    except Exception as exc:
        print(f"✗ Error indexando taxonomías: {exc}")
        traceback.print_exc()
        return False


def run_map_offers() -> bool:
    _separator("PASO 5 — Mapping de ofertas (map_offers)")
    try:
        from rag.map_offers import main as map_main
        map_main()
        print("✓ Mapping de ofertas completado correctamente.")
        return True
    except Exception as exc:
        print(f"✗ Error en mapping de ofertas: {exc}")
        traceback.print_exc()
        return False


def run_pipeline() -> None:
    _separator("PIPELINE — Inicio de ciclo")

    # Paso 3: LLM (puede fallar por tokens)
    llm_ok = run_llm_processing()

    # Pasos 4 y 5: SIEMPRE se ejecutan, incluso si paso 3 falló
    tax_ok = run_index_taxonomy()
    map_ok = run_map_offers()

    # Resumen
    _separator("PIPELINE — Resumen del ciclo")
    print(f"  LLM extraction:    {'✓ OK' if llm_ok else '⚠ Parcial / Error'}")
    print(f"  Index taxonomías:  {'✓ OK' if tax_ok else '✗ Error'}")
    print(f"  Map ofertas:       {'✓ OK' if map_ok else '✗ Error'}")

    if llm_ok and tax_ok and map_ok:
        print("\n  Resultado: Pipeline completado al 100%.")
    elif not llm_ok and tax_ok and map_ok:
        print("\n  Resultado: LLM parcial — las ofertas procesadas fueron mapeadas.")
        print("  → El próximo ciclo retomará las ofertas pendientes.")
    else:
        print("\n  Resultado: Hubo errores. Revisar logs arriba.")


def main() -> None:
    print(f"Pipeline runner iniciado — ciclo cada {INTERVAL_HOURS}h")
    print(f"Primera ejecución: {_now()}\n")

    while True:
        try:
            run_pipeline()
        except Exception as exc:
            print(f"\n✗ Error fatal en el pipeline: {exc}")
            traceback.print_exc()

        print(f"\n⏳ Esperando {INTERVAL_HOURS}h hasta el próximo ciclo...")
        print(f"   Próxima ejecución estimada: ver logs\n")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
