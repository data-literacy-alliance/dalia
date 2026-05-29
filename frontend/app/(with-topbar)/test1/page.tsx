import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import Link from 'next/link';

const TASKS = [
  {
    id: 'browse',
    label: 'Looking for Content',
    description: 'Search and discover contents on DALIA',
    link: '/',
  },
  {
    id: 'curate',
    label: 'Curate Contents',
    description: 'Create, manage, and organize new contents for DALIA',
    link: '/profile',
  },
];

export default async function Page({}: Props) {
  return (
    <div className="flex min-h-[40rem] flex-1 flex-col items-center justify-center p-6">
      <h1 className="mb-4 text-2xl font-semibold">Please select your role</h1>
      <div className="grid w-full max-w-md gap-4">
        {TASKS.map((task) => (
          <Link key={task.id} href={task.link}>
            <Card
              key={task.id}
              className={`cursor-pointer border transition-all hover:bg-gray-50 hover:shadow-lg focus:bg-gray-50 focus:shadow-lg`}
            >
              <CardHeader className="flex items-center justify-between">
                <CardTitle>{task.label}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-center text-sm text-gray-500 dark:text-gray-400">
                  {task.description}
                </p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}

type Props = {};
