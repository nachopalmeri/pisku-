# React + TypeScript

## Purpose
TypeScript-first React patterns for building type-safe, scalable component trees.

## Project Setup
```bash
npm create vite@latest my-app -- --template react-ts
cd my-app && npm install
```

## Component Patterns
```tsx
// Typed props
interface ButtonProps {
  label: string;
  onClick: () => void;
  variant?: 'primary' | 'ghost';
  disabled?: boolean;
}

const Button: React.FC<ButtonProps> = ({ label, onClick, variant = 'primary', disabled = false }) => (
  <button className={`btn btn-${variant}`} onClick={onClick} disabled={disabled}>
    {label}
  </button>
);

// Children pattern
interface CardProps {
  title: string;
  children: React.ReactNode;
}
```

## Hooks
```tsx
// useState with type
const [count, setCount] = useState<number>(0);
const [user, setUser] = useState<User | null>(null);

// useEffect with cleanup
useEffect(() => {
  const controller = new AbortController();
  fetchData(controller.signal).then(setData);
  return () => controller.abort();
}, [id]);

// useRef
const inputRef = useRef<HTMLInputElement>(null);

// Custom hook
function useLocalStorage<T>(key: string, initial: T): [T, (v: T) => void] {
  const [value, setValue] = useState<T>(() => {
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : initial;
  });
  const set = (v: T) => { setValue(v); localStorage.setItem(key, JSON.stringify(v)); };
  return [value, set];
}
```

## Context API
```tsx
interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  // ... implementation
  return <AuthContext.Provider value={{ user, login, logout }}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
};
```

## API Calls
```tsx
// Generic fetch hook
function useFetch<T>(url: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(url)
      .then(r => r.json())
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [url]);

  return { data, loading, error };
}
```

## Key Patterns
- Prefer `interface` over `type` for component props
- Use `React.FC<Props>` or just typed function declaration
- `Partial<T>` for update payloads, `Required<T>` for strict forms
- `as const` for literal type arrays
- `discriminated unions` for state machines
