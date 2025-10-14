import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    status: 'healthy',
    service: 'revrx-frontend',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
  });
}
