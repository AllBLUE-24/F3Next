import { describe, expect, it } from 'vitest';

import { getDevAuthUser, isDevAuthBypassEnabled } from '@/utils/dev-auth';

describe('dev-auth', () => {
  it('is disabled outside development', () => {
    expect(isDevAuthBypassEnabled()).toBe(false);
  });

  it('returns stable dev user defaults', () => {
    const user = getDevAuthUser();
    expect(user.id).toBe('dev-user-local-001');
    expect(user.email).toBe('dev@f3next.local');
  });
});
