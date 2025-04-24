"""Contains the class OrderShipping"""
from datetime import datetime, timezone
import hashlib

class AccountDeposit():
    """Class representing the information required for a deposit into an account."""
    # Corrected class docstring

    def __init__(self,
                 to_iban: str,
                 deposit_amount: float):
        self.__alg = "SHA-256"
        self.__type = "DEPOSIT"
        self.__to_iban = to_iban
        self.__deposit_amount = deposit_amount
        justnow = datetime.now(timezone.utc)
        # Renamed __deposit_date to __deposit_timestamp for clarity
        self.__deposit_timestamp = datetime.timestamp(justnow)


    def to_json(self):
        """returns the object data in json format"""
        return {"alg": self.__alg,
                "type": self.__type,
                "to_iban": self.__to_iban,
                "deposit_amount": self.__deposit_amount,
                "deposit_timestamp": self.__deposit_timestamp, # Updated name
                "deposit_signature": self.deposit_signature}

    def _get_signature_string(self): # Renamed from __signature_string,
        # use single underscore convention
        """Composes the string to be used for generating the deposit signature."""
        # Improved docstring
        # Using f-string for slightly better readability
        return (f"{{alg:{self.__alg},typ:{self.__type},iban:{self.__to_iban},"
                f"amount:{self.__deposit_amount},deposit_date:{self.__deposit_timestamp}}}")
        # Updated name

    @property
    def to_iban(self):
        """Property representing the IBAN the deposit is made to.""" # Corrected docstring
        return self.__to_iban

    @to_iban.setter
    def to_iban(self, value):
        self.__to_iban = value

    @property
    def deposit_amount(self):
        """Property representing the amount deposited.""" # Corrected docstring
        return self.__deposit_amount

    @deposit_amount.setter
    def deposit_amount(self, value):
        self.__deposit_amount = value

    @property
    def deposit_timestamp(self): # Renamed property to match attribute
        """Read-only property representing the timestamp when the deposit object was created."""
        # Corrected docstring
        return self.__deposit_timestamp
    # Removed setter for timestamp as it's set internally on creation

    @property
    def deposit_signature( self ):
        """Returns the sha256 signature of the deposit data.""" # Corrected the docstring
        # Changed call to use the renamed private method
        return hashlib.sha256(self._get_signature_string().encode()).hexdigest()
