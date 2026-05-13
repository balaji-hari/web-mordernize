// `import 'reflect-metadata';` MUST be the first import; Nest's DI
// relies on the polyfill being loaded before any decorator is parsed.
// Do not move, reorder, or remove this line.
import 'reflect-metadata';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Dev CORS allow-list — tighten before any non-local deploy.
  app.enableCors({
    origin: [
      'http://localhost:5173',
      'http://localhost:3000',
      'http://localhost:4200',
    ],
    credentials: true,
  });

  // Bind to 3001 by default — Next.js dev uses 3000, so the Nest default
  // collides. PORT env var still wins.
  await app.listen(process.env.PORT ?? 3001);
}
bootstrap();
