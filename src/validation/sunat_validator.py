"""
Módulo de Validación Fiscal SUNAT
Valida RUCs peruanos usando el algoritmo de Módulo 11
y otras reglas fiscales de SUNAT.
"""

from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal, ROUND_HALF_UP
import re
from datetime import datetime


class SUNATValidator:
    """
    Validador de datos fiscales según normativa SUNAT (Perú).
    """

    # Constantes fiscales
    IGV_RATE = Decimal("0.18")  # 18% IGV
    RUC_LENGTH = 11

    # Tipos de RUC según primer dígito
    RUC_TYPES = {
        "10": "DNI - Persona Natural",
        "15": "Extranjeros - Persona Natural",
        "17": "RUC Temporal",
        "20": "Persona Jurídica"
    }

    def __init__(self, strict_mode: bool = False):
        """
        Args:
            strict_mode: Si True, rechaza cualquier error. Si False, permite correcciones
        """
        self.strict_mode = strict_mode

    def validate_ruc(self, ruc: str) -> Tuple[bool, Optional[str]]:
        """
        Valida un RUC peruano usando el algoritmo de Módulo 11.

        El algoritmo multiplica cada dígito por factores específicos,
        suma los productos, y verifica que el dígito verificador sea correcto.

        Args:
            ruc: RUC a validar (string de 11 dígitos)

        Returns:
            Tupla (es_válido, mensaje_error)
        """
        # Limpiar RUC (eliminar espacios, guiones, etc.)
        ruc_clean = re.sub(r'[^0-9]', '', str(ruc))

        # Verificar longitud
        if len(ruc_clean) != self.RUC_LENGTH:
            return False, f"RUC debe tener {self.RUC_LENGTH} dígitos (tiene {len(ruc_clean)})"

        # Verificar tipo de RUC válido
        tipo = ruc_clean[:2]
        if tipo not in self.RUC_TYPES:
            return False, f"Tipo de RUC inválido: {tipo}"

        # Algoritmo de Módulo 11
        # Factores de multiplicación: 5,4,3,2,7,6,5,4,3,2
        factores = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]

        suma = 0
        for i in range(10):
            suma += int(ruc_clean[i]) * factores[i]

        # Calcular dígito verificador
        resto = suma % 11
        digito_verificador_esperado = 11 - resto

        # Casos especiales
        if digito_verificador_esperado == 11:
            digito_verificador_esperado = 0
        elif digito_verificador_esperado == 10:
            digito_verificador_esperado = 1

        # Verificar último dígito
        digito_verificador_actual = int(ruc_clean[10])

        if digito_verificador_actual != digito_verificador_esperado:
            return False, f"Dígito verificador incorrecto. Esperado: {digito_verificador_esperado}, Actual: {digito_verificador_actual}"

        return True, None

    def calculate_ruc_check_digit(self, ruc_base: str) -> Optional[str]:
        """
        Calcula el dígito verificador para los primeros 10 dígitos de un RUC.

        Args:
            ruc_base: Primeros 10 dígitos del RUC

        Returns:
            RUC completo de 11 dígitos o None si inválido
        """
        if len(ruc_base) != 10 or not ruc_base.isdigit():
            return None

        factores = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
        suma = sum(int(ruc_base[i]) * factores[i] for i in range(10))

        resto = suma % 11
        digito_verificador = 11 - resto

        if digito_verificador == 11:
            digito_verificador = 0
        elif digito_verificador == 10:
            digito_verificador = 1

        return ruc_base + str(digito_verificador)

    def validate_invoice_totals(
        self,
        subtotal: float,
        igv: float,
        total: float,
        tolerance: float = 0.01
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida que los totales de la factura sean matemáticamente correctos.
        Verifica: subtotal + IGV = total y que IGV = subtotal * 18%

        Args:
            subtotal: Subtotal (base imponible)
            igv: IGV (18%)
            total: Total
            tolerance: Tolerancia para diferencias de redondeo

        Returns:
            Tupla (es_válido, mensaje_error)
        """
        # Convertir a Decimal para precisión
        sub = Decimal(str(subtotal))
        igv_val = Decimal(str(igv))
        tot = Decimal(str(total))

        # Calcular IGV esperado
        igv_esperado = (sub * self.IGV_RATE).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        )

        # Calcular total esperado
        total_esperado = sub + igv_val

        # Verificar IGV
        diff_igv = abs(igv_val - igv_esperado)
        if diff_igv > Decimal(str(tolerance)):
            return False, f"IGV incorrecto. Esperado: {igv_esperado}, Actual: {igv_val}"

        # Verificar total
        diff_total = abs(tot - total_esperado)
        if diff_total > Decimal(str(tolerance)):
            return False, f"Total incorrecto. Esperado: {total_esperado}, Actual: {tot}"

        return True, None

    def validate_invoice_date(
        self,
        fecha: str,
        formato: str = "%d/%m/%Y"
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida que la fecha de factura sea válida.

        Args:
            fecha: Fecha como string
            formato: Formato de fecha esperado

        Returns:
            Tupla (es_válido, mensaje_error)
        """
        try:
            fecha_obj = datetime.strptime(fecha, formato)

            # Verificar que no sea fecha futura
            if fecha_obj > datetime.now():
                return False, "Fecha no puede ser futura"

            # Verificar que no sea muy antigua (facturas > 10 años sospechosas)
            edad_anos = (datetime.now() - fecha_obj).days / 365.25
            if edad_anos > 10:
                return False, f"Fecha muy antigua ({edad_anos:.1f} años)"

            return True, None

        except ValueError as e:
            return False, f"Formato de fecha inválido: {str(e)}"

    def validate_invoice_number(
        self,
        serie: str,
        numero: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida formato de serie y número de factura según SUNAT.

        Formato típico: Serie (4 caracteres) - Número (hasta 8 dígitos)
        Ejemplo: F001-00012345

        Args:
            serie: Serie de la factura (ej. "F001")
            numero: Número correlativo (ej. "00012345")

        Returns:
            Tupla (es_válido, mensaje_error)
        """
        # Validar serie
        if not re.match(r'^[A-Z]\d{3}$', serie):
            return False, f"Serie inválida: {serie}. Formato esperado: [A-Z]###"

        # Validar número
        if not numero.isdigit():
            return False, f"Número debe ser numérico: {numero}"

        if len(numero) > 8:
            return False, f"Número muy largo: {numero} (máximo 8 dígitos)"

        numero_int = int(numero)
        if numero_int <= 0:
            return False, f"Número debe ser positivo: {numero}"

        return True, None

    def validate_full_invoice(
        self,
        invoice_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Valida todos los campos de una factura extraída.

        Args:
            invoice_data: Diccionario con datos de la factura

        Returns:
            Diccionario con resultados de validación
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "corrected_fields": {}
        }

        # Validar RUC emisor
        if "ruc_e" in invoice_data or "ruc_emisor" in invoice_data:
            ruc_e = invoice_data.get("ruc_e") or invoice_data.get("ruc_emisor")
            valid, error = self.validate_ruc(ruc_e)
            if not valid:
                results["errors"].append(f"RUC Emisor: {error}")
                results["valid"] = False

        # Validar RUC receptor
        if "ruc_r" in invoice_data or "ruc_receptor" in invoice_data:
            ruc_r = invoice_data.get("ruc_r") or invoice_data.get("ruc_receptor")
            valid, error = self.validate_ruc(ruc_r)
            if not valid:
                results["errors"].append(f"RUC Receptor: {error}")
                results["valid"] = False

        # Validar totales
        if all(k in invoice_data for k in ["sub", "igv", "tot"]):
            try:
                subtotal = float(invoice_data["sub"])
                igv = float(invoice_data["igv"])
                total = float(invoice_data["tot"])

                valid, error = self.validate_invoice_totals(subtotal, igv, total)
                if not valid:
                    results["errors"].append(f"Totales: {error}")
                    results["valid"] = False
            except ValueError as e:
                results["errors"].append(f"Error convirtiendo totales: {str(e)}")
                results["valid"] = False

        # Validar fecha
        if "fec" in invoice_data or "fecha_emision" in invoice_data:
            fecha = invoice_data.get("fec") or invoice_data.get("fecha_emision")
            valid, error = self.validate_invoice_date(fecha)
            if not valid:
                results["warnings"].append(f"Fecha: {error}")

        # Validar número de factura
        if "ser" in invoice_data and "num" in invoice_data:
            serie = invoice_data["ser"]
            numero = invoice_data["num"]
            valid, error = self.validate_invoice_number(serie, numero)
            if not valid:
                results["warnings"].append(f"Número factura: {error}")

        return results

    def auto_correct_ruc(self, ruc: str) -> Optional[str]:
        """
        Intenta corregir automáticamente un RUC con errores menores.

        Args:
            ruc: RUC potencialmente erróneo

        Returns:
            RUC corregido o None si no se puede corregir
        """
        # Limpiar
        ruc_clean = re.sub(r'[^0-9]', '', str(ruc))

        # Si tiene longitud incorrecta, intentar pad con ceros
        if len(ruc_clean) == 10:
            # Calcular dígito verificador
            return self.calculate_ruc_check_digit(ruc_clean)

        # Si tiene 11 dígitos, verificar si solo el check digit está mal
        if len(ruc_clean) == 11:
            ruc_base = ruc_clean[:10]
            ruc_correcto = self.calculate_ruc_check_digit(ruc_base)
            if ruc_correcto != ruc_clean:
                return ruc_correcto

        return None


def validate_ruc(ruc: str) -> bool:
    """
    Función de conveniencia para validar un RUC.

    Args:
        ruc: RUC a validar

    Returns:
        True si es válido, False si no
    """
    validator = SUNATValidator()
    valid, _ = validator.validate_ruc(ruc)
    return valid


def validate_invoice(invoice_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Función de conveniencia para validar una factura completa.

    Args:
        invoice_data: Datos de la factura

    Returns:
        Resultados de validación
    """
    validator = SUNATValidator()
    return validator.validate_full_invoice(invoice_data)
