import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import App from '../App'

afterEach(() => {
  cleanup()
})

describe('App', () => {
  it('renders the route search input UI', () => {
    render(<App />)

    expect(
      screen.getByRole('heading', { name: /출발지와 목적지를 입력해 이동 조건을 설정하세요/i }),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('출발지')).toBeInTheDocument()
    expect(screen.getByLabelText('목적지')).toBeInTheDocument()
    expect(screen.getByLabelText('장애인 콜택시')).toBeChecked()
    expect(screen.getByLabelText('지하철')).toBeChecked()
    expect(screen.getByLabelText('저상버스')).toBeChecked()
    expect(screen.getByLabelText('시간 최소')).toBeChecked()
    expect(screen.getByRole('button', { name: '경로검색' })).toBeDisabled()
  })

  it('allows users to enter search conditions and submit them', () => {
    render(<App />)

    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
    fireEvent.change(screen.getByLabelText('목적지'), { target: { value: '서울역' } })
    fireEvent.click(screen.getByLabelText('도보 최소'))

    const searchButton = screen.getByRole('button', { name: '경로검색' })
    expect(searchButton).toBeEnabled()

    fireEvent.click(searchButton)

    expect(
      screen.getByText(/서울시청에서 서울역까지 장애인 콜택시, 지하철, 저상버스 기준으로 도보 최소 경로를 검색합니다/),
    ).toBeInTheDocument()
  })
})
