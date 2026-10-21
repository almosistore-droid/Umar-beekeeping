import { render, screen } from '@testing-library/react'
import { DeveloperCredit } from '../components/DeveloperCredit'

it('shows the developer: Developed by Fayziumar LLC', () => {
  render(<DeveloperCredit />)
  const credit = screen.getByRole('contentinfo', { name: 'Developed by Fayziumar LLC' })
  expect(credit).toHaveTextContent('Developed by')
  expect(credit).toHaveTextContent('Fayziumar LLC')
})
