interface Props {
  size?: number
  color?: string
}

export function WheelMark({ size = 22, color = 'var(--dl-bone)' }: Props) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" aria-hidden>
      <g transform="translate(32,32)" stroke={color} strokeWidth="3.5" fill="none">
        <circle r="27" />
        <circle r="18" />
        <circle r="7" fill={color} stroke="none" />
        <line x1="0" y1="-27" x2="0" y2="27" />
        <line x1="-27" y1="0" x2="27" y2="0" />
        <line x1="-19.1" y1="-19.1" x2="19.1" y2="19.1" />
        <line x1="-19.1" y1="19.1" x2="19.1" y2="-19.1" />
      </g>
    </svg>
  )
}
