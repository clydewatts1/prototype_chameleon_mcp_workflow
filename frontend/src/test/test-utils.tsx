/**
 * Test utilities and custom render function
 * Simplified version without providers for basic component testing
 */
import React, { ReactElement } from 'react';
import { render, RenderOptions, screen } from '@testing-library/react';
import * as userEvent from '@testing-library/user-event';

// Simple render without providers (use this for simple component tests)
const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>,
) => render(ui, options);

// Re-export everything
export * from '@testing-library/react';
export { customRender as render, userEvent, screen };
