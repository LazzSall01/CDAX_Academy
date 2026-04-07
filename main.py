from app.config import obtener_configuracion

if __name__ == "__main__":
    import uvicorn

    config = obtener_configuracion()

    if config.MODO_DESARROLLO:
        print("\n" + "=" * 50)
        print("  DENTAL MODERN ACADEMY - MODO DESARROLLO")
        print("=" * 50)
        print(f"  URL: http://localhost:8000")
        print(f"  Docs: http://localhost:8000/docs")
        print("=" * 50 + "\n")

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=config.MODO_DESARROLLO)
