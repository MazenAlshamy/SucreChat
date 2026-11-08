export default function TextField({
  id,
  label,
  value,
  onChange,
  placeholder,
  type = "text",
  required = false,
  multiline = false,
  autoComplete,
  maxLength,
  inputMode,
  pattern,
}) {
  return (
    <div className="form-field">
      <label htmlFor={id}>{label}</label>
      {multiline ? (
        <textarea
          id={id}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          required={required}
        />
      ) : (
        <input
          id={id}
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          required={required}
          autoComplete={autoComplete}
          maxLength={maxLength}
          inputMode={inputMode}
          pattern={pattern}
        />
      )}
    </div>
  );
}
