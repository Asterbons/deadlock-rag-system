interface Props {
  size?: number
  color?: string
}

export function WheelMark({ size = 22 }: Props) {
  return (
    <img
      src="/dl.png"
      width={size}
      height={size}
      alt="Deadlock"
      aria-hidden
      style={{ objectFit: 'contain', display: 'block' }}
    />
  )
}
