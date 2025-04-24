"""Account manager module """
import re
import json
from datetime import datetime, timezone
from uc3m_money.account_management_exception import AccountManagementException
from uc3m_money.account_management_config import (TRANSFERS_STORE_FILE,
                                        DEPOSITS_STORE_FILE,
                                        TRANSACTIONS_STORE_FILE,
                                        BALANCES_STORE_FILE)

from uc3m_money.transfer_request import TransferRequest
from uc3m_money.account_deposit import AccountDeposit

class _SingletonMeta(type):
    """
    Metaclass enforcing that only one instance of a class exists.
    """
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class AccountManager:
    """Class for providing the methods for managing the orders"""
    def __init__(self):
        pass

    @staticmethod
    def validate_iban(iban_input: str):
        """
    Calcula el dígito de control de un IBAN español.

    Args:
        ic (str): El IBAN sin los dos últimos dígitos (dígito de control).

    Returns:
        str: El dígito de control calculado.
        """
        iban_pattern = re.compile(r"^ES[0-9]{22}")
        match = iban_pattern.fullmatch(iban_input)
        if not match:
            raise AccountManagementException("Invalid IBAN format")
        iban = iban_input
        original_code = iban[2:4]
        #replacing the control
        iban = iban[:2] + "00" + iban[4:]
        iban = iban[4:] + iban[:4]

        # Replace letters with numeric equivalents (A=10,...,Z=35)
        iban = ''.join(
            str(ord(ch) - ord('A') + 10) if 'A' <= ch <= 'Z' else ch
            for ch in iban
        )

        # Mover los cuatro primeros caracteres al final

        # Convertir la cadena en un número entero
        int_i = int(iban)

        # Calcular el módulo 97
        mod = int_i % 97

        # Calcular el dígito de control (97 menos el módulo)
        control_digit = 98 - mod

        if int(original_code) != control_digit:
            #print(control_digit)
            raise AccountManagementException("Invalid IBAN control digit")

        return iban_input

    def validate_concept(self, concept: str):
        """regular expression for checking the minimum and maximum length as well as
        the allowed characters and spaces restrictions
        there are other ways to check this"""
        concept_pattern = re.compile(r"^(?=^.{10,30}$)([a-zA-Z]+(\s[a-zA-Z]+)+)$")

        match = concept_pattern.fullmatch(concept)
        if not match:
            raise AccountManagementException ("Invalid concept format")

    def validate_transfer_date(self, date_str):
        """validates the arrival date format  using regex"""
        date_pattern = re.compile(r"^(([0-2]\d|3[0-1])\/(0\d|1[0-2])\/\d\d\d\d)$")
        match = date_pattern.fullmatch(date_str)
        if not match:
            raise AccountManagementException("Invalid date format")

        try:
            parsed_date = datetime.strptime(date_str, "%d/%m/%Y").date()
        except ValueError as ex:
            raise AccountManagementException("Invalid date format") from ex

        if parsed_date < datetime.now(timezone.utc).date():
            raise AccountManagementException("Transfer date must be today or later.")

        if parsed_date.year < 2025 or parsed_date.year > 2050:
            raise AccountManagementException("Invalid date format")
        return date_str
    #pylint: disable=too-many-arguments
    def transfer_request(self, from_iban: str,
                         to_iban: str,
                         concept: str,
                         transfer_type: str,
                         date: str,
                         amount: float)->str:
        """first method: receives transfer info and
        stores it into a file"""
        self.validate_iban(from_iban)
        self.validate_iban(to_iban)
        self.validate_concept(concept)
        transfer_type_pattern = re.compile(r"(ORDINARY|INMEDIATE|URGENT)")
        match = transfer_type_pattern.fullmatch(transfer_type)
        if not match:
            raise AccountManagementException("Invalid transfer type")
        self.validate_transfer_date(date)

        try:
            amount_value  = float(amount)
        except ValueError as exc:
            raise AccountManagementException("Invalid transfer amount") from exc

        amount_str = str(amount_value)
        if '.' in amount_str:
            decimal_count = len(amount_str.split('.')[1])
            if decimal_count > 2:
                raise AccountManagementException("Invalid transfer amount")

        if amount_value < 10 or amount_value > 10000:
            raise AccountManagementException("Invalid transfer amount")

        new_transfer = TransferRequest(from_iban=from_iban,
                                     to_iban=to_iban,
                                     transfer_concept=concept,
                                     transfer_type=transfer_type,
                                     transfer_date=date,
                                     transfer_amount=amount)

        try:
            with open(TRANSFERS_STORE_FILE, "r", encoding="utf-8", newline="") as file:
                transfer_list = json.load(file)
        except FileNotFoundError:
            transfer_list = []
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex

        for existing_transfer in transfer_list:
            if (existing_transfer["from_iban"] == new_transfer.from_iban and
                    existing_transfer["to_iban"] == new_transfer.to_iban and
                    existing_transfer["transfer_date"] == new_transfer.transfer_date and
                    existing_transfer["transfer_amount"] == new_transfer.transfer_amount and
                    existing_transfer["transfer_concept"] == new_transfer.transfer_concept and
                    existing_transfer["transfer_type"] == new_transfer.transfer_type):
                raise AccountManagementException("Duplicated transfer in transfer list")

        transfer_list.append(new_transfer.to_json())

        try:
            with open(TRANSFERS_STORE_FILE, "w", encoding="utf-8", newline="") as file:
                json.dump(transfer_list, file, indent=2)
        except FileNotFoundError as ex:
            raise AccountManagementException("Wrong file  or file path") from ex
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex

        return new_transfer.transfer_code

    def deposit_into_account(self, input_file:str)->str:
        """manages the deposits received for accounts"""
        try:
            with open(input_file, "r", encoding="utf-8", newline="") as file:
                input_data = json.load(file)
        except FileNotFoundError as ex:
            raise AccountManagementException("Error: file input not found") from ex
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex

        # comprobar valores del fichero
        try:
            deposit_iban = input_data["IBAN"]
            deposit_amount = input_data["AMOUNT"]
        except KeyError as e:
            raise AccountManagementException("Error - Invalid Key in JSON") from e

        deposit_iban = self.validate_iban(deposit_iban)
        deposit_amount_pattern = re.compile(r"^EUR [0-9]{4}\.[0-9]{2}")
        match = deposit_amount_pattern.fullmatch(deposit_amount)
        if not match:
            raise AccountManagementException("Error - Invalid deposit amount")

        deposit_amount_value = float(deposit_amount[4:])
        if deposit_amount_value == 0:
            raise AccountManagementException("Error - Deposit must be greater than 0")

        deposit_obj = AccountDeposit(to_iban=deposit_iban,
                                     deposit_amount=deposit_amount_value)

        try:
            with open(DEPOSITS_STORE_FILE, "r", encoding="utf-8", newline="") as file:
                deposit_list = json.load(file)
        except FileNotFoundError as ex:
            deposit_list = []
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex

        deposit_list.append(deposit_obj.to_json())

        try:
            with open(DEPOSITS_STORE_FILE, "w", encoding="utf-8", newline="") as file:
                json.dump(deposit_list, file, indent=2)
        except FileNotFoundError as ex:
            raise AccountManagementException("Wrong file  or file path") from ex
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex

        return deposit_obj.deposit_signature

    def read_transactions_file(self):
        """loads the content of the transactions file
        and returns a list"""
        try:
            with open(TRANSACTIONS_STORE_FILE, "r", encoding="utf-8", newline="") as file:
                input_list = json.load(file)
        except FileNotFoundError as ex:
            raise AccountManagementException("Wrong file  or file path") from ex
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex
        return input_list

    def calculate_balance(self, iban:str)->bool:
        """calculate the balance for a given iban"""
        iban = self.validate_iban(iban)
        transactions = self.read_transactions_file()
        iban_found = False
        balance_sum = 0
        for transaction in transactions:
            #print(transaction["IBAN"] + " - " + iban)
            if transaction["IBAN"] == iban:
                balance_sum += float(transaction["amount"])
                iban_found = True
        if not iban_found:
            raise AccountManagementException("IBAN not found")

        last_balance = {"IBAN": iban,
                        "time": datetime.timestamp(datetime.now(timezone.utc)),
                        "BALANCE": balance_sum}

        try:
            with open(BALANCES_STORE_FILE, "r", encoding="utf-8", newline="") as file:
                balance_list = json.load(file)
        except FileNotFoundError:
            balance_list = []
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex

        balance_list.append(last_balance)

        try:
            with open(BALANCES_STORE_FILE, "w", encoding="utf-8", newline="") as file:
                json.dump(balance_list, file, indent=2)
        except FileNotFoundError as ex:
            raise AccountManagementException("Wrong file  or file path") from ex
        return True