import threading

class BasicRotator:
    def __init__(self, item_list: list):
        self._item_list = item_list
        self._index = 0
        self._lock = threading.Lock()

    def __len__(self):
        return len(self._item_list)
    
    def __next__(self):
        with self._lock:
            self._index = (self._index + 1) % len(self._item_list)
            item = self._item_list[self._index]
            return item
    
    def remove(self, item: str):
        with self._lock:
            if item in self._item_list:
                self._item_list.remove(item)

class ComboRotator:
    def __init__(self, combo_list: list):
        self._lock = threading.Lock()
        self._passwords = {}
        self._combos = []
        self._index = 0
        self._length = 0
        self._setup(combo_list)

    def __len__(self):
        return self._length
    
    def __next__(self):
        with self._lock:
            while True:
                if not self._length:
                    raise StopIteration
                self._index = self._index % len(self._combos)
                credential, password_list = self._combos[self._index]
                if not password_list:
                    del self._combos[self._index]
                    continue
                self._index += 1
                self._length -= 1
                return (
                    credential,
                    password_list.pop(),
                    "Email" if "@" in credential else "Username"
                )

    def clear(self, credential: str):
        with self._lock:
            if (l := self._passwords.get(credential)):
                l.clear()
                
    def add(self, credential: str, password: str):
        credential = credential.lower()
        with self._lock:
            if (l := self._passwords.get(credential)):
                if not password in l:
                    l.add(password)
                    self._length += 1
            else:
                l = set((password,))
                self._passwords[credential] = l
                self._combos.append((credential, l))
                self._length += 1
    
    def _setup(self, combo_list: list):
        for credential, password in combo_list:
            if not credential in self._passwords:
                self._passwords[credential] = set((password,))
                self._length += 1
            else:
                if not password in self._passwords[credential]:
                    self._passwords[credential].add(password)
                    self._length += 1
        self._combos.extend(self._passwords.items())