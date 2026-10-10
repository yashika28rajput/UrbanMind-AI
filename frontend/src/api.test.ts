import { describe, expect, it } from 'vitest'
import { errorMessage } from './api'

describe('API error messages', () => {
  it('returns actionable field names for backend validation errors', () => {
    const error = {
      isAxiosError: true,
      response: {
        status: 422,
        data: {
          detail: [{
            loc: ['body', 'annual_vehicle_km'],
            msg: 'Input should be greater than 0',
          }],
        },
      },
    }

    expect(errorMessage(error)).toBe('annual_vehicle_km: Input should be greater than 0')
  })
})
