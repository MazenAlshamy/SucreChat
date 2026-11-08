export default function PageHeader({ kicker, title, description }) {
  return (
    <div>
      {kicker ? <p className="kicker">{kicker}</p> : null}
      <h1>{title}</h1>
      {description ? <p>{description}</p> : null}
    </div>
  );
}
