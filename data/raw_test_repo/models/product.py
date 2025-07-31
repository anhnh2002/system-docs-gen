# Copyright (c) Meta Platforms, Inc. and affiliates
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Item:
    """
    Summary:
    Represents an item with associated attributes for tracking and management in various contexts.

    Description:
    This class serves as a blueprint for creating items that can be tracked and managed within a system. Each item has attributes such as a unique code, a label, a value, a count, an optional expiration date, and a group classification. The primary motivation behind this class is to facilitate resource management, inventory tracking, or any scenario where items need to be monitored for validity and availability.

    Use this class when you need to represent items that may have a limited lifespan or quantity, such as in inventory systems, gaming resources, or token management. It provides methods to check the validity of an item and to modify its count, ensuring that operations on the item are safe and consistent.

    The class fits into larger systems by allowing for easy integration with resource management workflows, enabling developers to track item states and manage their lifecycle effectively.

    Example:
    ```python
    from datetime import datetime, timedelta

    # Create an item with a specific expiration date
    item = Item(code='A123', label='Sample Item', val=10.0, count=5, exp=datetime.now() + timedelta(days=1))

    # Check if the item is valid
    is_valid = item.check()  # Returns True if count > 0 and not expired

    # Modify the count of the item
    item.mod(2)  # Decreases count by 2, returns True
    ```

    Parameters:
    - code (str): A unique identifier for the item.
    - label (str): A descriptive name for the item.
    - val (float): The value associated with the item, representing its worth.
    - count (int): The quantity of the item available. Must be a non-negative integer.
    - exp (Optional[datetime]): An optional expiration date for the item. If set, the item will be considered invalid after this date.
    - grp (str): A classification group for the item, defaulting to 'misc'.

    Attributes:
    - code (str): The unique identifier for the item.
    - label (str): The name or description of the item.
    - val (float): The monetary or functional value of the item.
    - count (int): The current quantity of the item available, must be non-negative.
    - exp (Optional[datetime]): The expiration date of the item, if applicable.
    - grp (str): The group classification of the item, useful for categorization.
    """
    code: str
    label: str
    val: float
    count: int
    exp: Optional[datetime] = None
    grp: str = 'misc'

    def check(self) -> bool:
        """
        Validates the current object's state based on count and expiration.

        Checks whether the object is still valid by verifying two key conditions:
        1. The object's count is greater than zero
        2. The object has not exceeded its expiration timestamp

        This method is typically used to determine if an object is still usable
        or has become stale/invalid. It provides a quick state validation check
        that can be used in resource management, token validation, or lifecycle
        tracking scenarios.

        Returns:
            bool: True if the object is valid (count > 0 and not expired),
                  False otherwise.
        """
        if self.count <= 0:
            return False
        if self.exp and datetime.now() > self.exp:
            return False
        return True

    def mod(self, n: int=1) -> bool:
        """
        Summary:
        Determines if the current count can be decremented by a specified value.

        Description:
        This method checks if the `count` attribute is greater than or equal to the provided integer `n`. If so, it decrements `count` by `n` and returns `True`. If `count` is less than `n`, it returns `False`, indicating that the operation could not be performed.

        Use this function when managing resources or operations that require a controlled decrement of a count, ensuring that the count does not drop below zero. This is particularly useful in scenarios such as resource allocation, gaming mechanics, or iterative processes.

        The method is integral to classes that require precise control over a count, allowing for safe decrements while maintaining the integrity of the count value.

        Args:
        n (int, optional): The value to decrement from `count`. Must be a positive integer that does not exceed the current `count`. Default is 1.

        Returns:
        bool: Returns `True` if the decrement was successful (i.e., `count` was greater than or equal to `n`), otherwise returns `False`.

        Raises:
        No exceptions are raised by this method. Ensure that `n` is a positive integer and does not exceed the current `count` to avoid logical errors.

        Examples:
        ```python
        obj = YourClass()
        obj.count = 5
        result = obj.mod(2)  # result will be True, obj.count will be 3
        result = obj.mod(4)  # result will be False, obj.count remains 3
        result = obj.mod(0)  # result will be False, as n should be greater than 0
        result = obj.mod(-1) # result will be False, as n should be a positive integer
        ```
        """
        if self.count >= n:
            self.count -= n
            return True
        return False