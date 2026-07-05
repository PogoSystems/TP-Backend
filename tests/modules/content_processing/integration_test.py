import dataclasses
import json
from pathlib import Path
# Importa la clase real en lugar del Stub
from modules.content_processing.infrastructure.extractors.pdf_extractor import PdfContentExtractor 
from modules.content_processing.application.services.parsing.content_preparation_service import ContentPreparationService
from modules.content_processing.infrastructure.storage.local_document_store import LocalDocumentStore

def test_preparation_service_procesa_pdf_real(tmp_path: Path) -> None:
    # 1. Localizar el PDF real en tu carpeta de fixtures
    # __file__ hace referencia al archivo actual (test_documentos.py)
    directorio_actual = Path(__file__).parent
    pdf_real_path = directorio_actual / "fixtures" / "muestra.pdf"
    
    # Asegurarnos de que el archivo de prueba realmente existe antes de seguir
    assert pdf_real_path.exists(), "Falta el PDF de prueba en la carpeta fixtures"

    # 2. Instanciar los servicios con el Extractor REAL
    store = LocalDocumentStore(base_path=tmp_path)
    extractor = PdfContentExtractor() # ¡Usamos el código de producción!
    service = ContentPreparationService(document_store=store, extractor=extractor)

    # 3. Ejecutar el proceso con el PDF real
    prepared = service.prepare_pdf(source_path=pdf_real_path, title="Documento Real")

    # 4. Validaciones de Integración
    assert prepared.raw.document_type == "pdf"
    assert len(prepared.sections) > 0, "El extractor no detectó ninguna sección en el PDF real"
# --- EXPORTAR PARA INSPECCIÓN VISUAL ---
    # Esto creará un archivo llamado "resultado_debug.md" en la raíz de tu proyecto
    archivo_salida = pdf_real_path.with_suffix(".json")
    
    # Función robusta para desarmar el objeto a un diccionario puro de Python
    def object_to_dict(obj):
        if dataclasses.is_dataclass(obj):
            # Si es un dataclass (muy probable por la imagen), esto lo desarma perfectamente, incluyendo objetos anidados
            return dataclasses.asdict(obj)
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        if hasattr(obj, 'dict'):
            return obj.dict()
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)

    # Convertimos a diccionario y luego a JSON con indentación de 4 espacios
    datos_diccionario = object_to_dict(prepared)

    json_data = json.dumps(
        datos_diccionario, 
        indent=4, 
        ensure_ascii=False, 
        default=str
    )
    # Guardamos el JSON completo
    archivo_salida.write_text(json_data, encoding="utf-8")
    print(prepared.raw.markdown)
    print(f"\n✅ Archivo de inspección generado en: {archivo_salida.absolute()}")